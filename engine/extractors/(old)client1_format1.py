# engine/extractors/client1_format1.py
# -------------------------------------------------------------
# Client 1 - Format 1 OCR Extractor (Two-Pass Architecture)
# PASS 1: Tesseract @ DPI 600 for ALL fields EXCEPT Delivery Address
# PASS 2: Calls delivery_address.extract_delivery_address_v2() with PaddleOCR
# Returns complete RAW dict with all fields
# -------------------------------------------------------------

import os
import re
import json
import shutil
import logging
import platform
from datetime import datetime
from collections import defaultdict
from difflib import get_close_matches
from typing import Dict, Any, Tuple, Optional, List

import pytesseract
from pdf2image import convert_from_path
from pytesseract import Output
from PIL import Image, ImageOps, ImageFilter

# Import the dedicated delivery address extractor (second pass)
# We'll try to import the structured API if available, otherwise fall back to v2
_HAS_DELIVERY_EXTRACTOR = False
_extract_delivery_struct = None
_extract_delivery_v2 = None
try:
    from engine.extractors.delivery_address import extract_delivery_address_struct, extract_delivery_address_v2
    _HAS_DELIVERY_EXTRACTOR = True
    _extract_delivery_struct = extract_delivery_address_struct
    _extract_delivery_v2 = extract_delivery_address_v2
except Exception as e:
    try:
        from engine.extractors.delivery_address import extract_delivery_address_v2
        _HAS_DELIVERY_EXTRACTOR = True
        _extract_delivery_v2 = extract_delivery_address_v2
    except Exception:
        _HAS_DELIVERY_EXTRACTOR = False
        print(f"Warning: delivery_address module not available: {e}")

# -------------------------
# Logging
# -------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
# Set to DEBUG for more detailed extraction logging, INFO for normal operation
logger.setLevel(logging.DEBUG if os.getenv("EXTRACTOR_DEBUG") else logging.INFO)

# -------------------------
# Where to save crop images (Windows absolute path as requested)
# -------------------------
CROPS_FOLDER = os.path.normpath(r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-main\crop")

# -------------------------
# Cross-platform: Tesseract / Poppler Detection
# -------------------------
def _detect_tesseract(explicit_cmd: Optional[str] = None) -> str:
    """Detect Tesseract executable across platforms"""
    if explicit_cmd and os.path.exists(explicit_cmd):
        pytesseract.pytesseract.tesseract_cmd = explicit_cmd
        return explicit_cmd

    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        pytesseract.pytesseract.tesseract_cmd = env_cmd
        return env_cmd

    found = shutil.which("tesseract")
    if found:
        pytesseract.pytesseract.tesseract_cmd = found
        return found

    system = platform.system()
    if system == "Windows":
        cands = [r"C:\Tesseract-OCR\tesseract.exe", r"C:\Program Files\Tesseract-OCR\tesseract.exe"]
    elif system == "Darwin":
        cands = ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/opt/local/bin/tesseract"]
    else:
        cands = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

    for c in cands:
        if os.path.exists(c):
            pytesseract.pytesseract.tesseract_cmd = c
            return c

    raise RuntimeError(
        "Tesseract not found. Install it or set TESSERACT_CMD environment variable."
    )


def _detect_poppler(explicit_path: Optional[str] = None) -> Optional[str]:
    """Detect Poppler path (Windows only)"""
    if platform.system() != "Windows":
        return None
    
    if explicit_path and os.path.isdir(explicit_path):
        return explicit_path
    
    env_p = os.getenv("POPPLER_PATH")
    if env_p and os.path.isdir(env_p):
        return env_p
    
    guesses = [
        r"C:\poppler-25.07.0\Library\bin",
        r"C:\Users\Public\poppler\bin",
        r"C:\poppler\bin",
    ]
    for g in guesses:
        if os.path.isdir(g):
            return g
    
    return None


# -------------------------
# OCR Preprocessing Helpers
# -------------------------
def _rotate_upright(img: Image.Image) -> Image.Image:
    """Detect and correct image rotation using Tesseract OSD"""
    try:
        osd = pytesseract.image_to_osd(img)
        for ln in osd.splitlines():
            if "Rotate:" in ln:
                deg = int(ln.split(":")[1].strip())
                if deg != 0:
                    return img.rotate(360 - deg, expand=True)
                break
    except Exception:
        pass
    return img


def _preprocess_variants_fast(img: Image.Image) -> List[Image.Image]:
    """Create preprocessed image variants for better OCR - enhanced for tilted text"""
    img = _rotate_upright(img)
    
    # Variant 1: Autocontrast grayscale
    g = ImageOps.autocontrast(img.convert("L"))
    
    # Variant 2: Sharpened version
    sharp = g.filter(ImageFilter.UnsharpMask(radius=1.4, percent=140, threshold=3))
    
    # Variant 3: Enhanced contrast and noise reduction for tilted text
    enhanced = g.copy()
    # Apply morphological operations to clean up text
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV format
        cv_img = np.array(enhanced)
        
        # Apply adaptive thresholding for better text separation
        thresh = cv2.adaptiveThreshold(cv_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Apply morphological operations to connect broken characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL
        enhanced = Image.fromarray(morph)
    except ImportError:
        # If OpenCV not available, use PIL operations
        enhanced = ImageOps.autocontrast(enhanced)
        enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))  # Noise reduction
    
    return [g, sharp, enhanced]


def _ocr_configs_fast(img: Image.Image) -> List[str]:
    """Run multiple Tesseract configs and return text results - enhanced for tilted text"""
    cfgs = [
        r"--oem 1 --psm 6 -c preserve_interword_spaces=1",
        r"--oem 1 --psm 4 -c preserve_interword_spaces=1",
        r"--oem 1 --psm 3 -c preserve_interword_spaces=1",  # Fully automatic page segmentation
        r"--oem 1 --psm 1 -c preserve_interword_spaces=1",  # Automatic page segmentation with OSD
        r"--oem 1 --psm 8 -c preserve_interword_spaces=1",  # Single word
        r"--oem 1 --psm 7 -c preserve_interword_spaces=1",  # Single text line
    ]
    outs: List[str] = []
    
    for cfg in cfgs:
        try:
            txt = pytesseract.image_to_string(img, config=cfg, lang="eng") or ""
            if txt.strip():
                outs.append(txt)
        except Exception:
            continue
    
    return outs


def _merge_text(blocks: List[str]) -> str:
    """Merge text blocks, removing duplicates while preserving order"""
    seen = set()
    merged = []
    
    for block in blocks:
        for ln in (block or "").splitlines():
            s = (ln or "").rstrip()
            if not s:
                continue
            key = s.strip()
            if key in seen:
                continue
            seen.add(key)
            merged.append(s)
    
    return "\n".join(merged)


# -------------------------
# Date Normalization & Parsing
# -------------------------
def normalize_for_dates(s: str) -> str:
    """Normalize OCR artifacts in date strings"""
    trans = str.maketrans({
        'O': '0', 'o': '0', 'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5', 'B': '8',
        '—': '-', '–': '-', '‚': ','
    })
    return s.translate(trans)


def try_parse_date(s: str):
    """Try parsing date string with multiple formats - ENHANCED for smudged OCR"""
    if not s:
        return None
    
    # Normalize OCR errors in date string (O→0, I→1, etc.)
    s = _normalize_ocr_smudge(s.strip())
    
    # Remove spaces around separators
    s = re.sub(r'\s*([./-])\s*', r'\1', s)
    
    for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", 
                "%d.%m.%y", "%d-%m-%y", "%d/%m/%y"]:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    
    return None


def extract_invoice_date(full_text: str, invoice_no: str = None) -> Optional[str]:
    """Extract invoice date - ENHANCED for smudged OCR (e.g., O5.1O.2O25 → 05.10.2025)"""
    norm = normalize_for_dates(full_text)
    # Allow OCR error characters in date patterns
    pat = re.compile(r'([0-3O]?[0-9OIlSs][./-][01O]?[0-9OIlSs][./-][0-9OIlSs]{2,4})')
    
    # First: Look near date/invoice keywords
    for line in norm.splitlines():
        if re.search(r'\b(date|invoice|d\.?o\.?|d\.?o\.?no)\b', line, re.IGNORECASE):
            m = pat.search(line)
            if m:
                dt = try_parse_date(m.group(1))
                if dt:
                    return dt.strftime("%d.%m.%Y")
    
    # Fallback: Any date pattern
    for m in pat.finditer(norm):
        dt = try_parse_date(m.group(1))
        if dt:
            return dt.strftime("%d.%m.%Y")
    
    # Last resort: Partial date fragment
    frag = re.search(r'([./-][01O]?[0-9OIlSs][./-][0-9OIlSs]{4})', norm)
    if frag:
        trial = ("01." if '.' in frag.group(1) else "01-") + frag.group(1).lstrip('./-')
        dt = try_parse_date(trial)
        if dt:
            return dt.strftime("%d.%m.%Y")
    
    return None


def find_value(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    """Generic regex value extractor"""
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


# -------------------------
# Field Extractors (PASS 1 - All except Delivery Address)
# -------------------------

def extract_invoice_no(text: str) -> Optional[str]:
    """Extract invoice/D.I. number - ENHANCED for smudged OCR"""
    U = (text or "").upper()
    
    def keep_digits(s: str) -> Optional[str]:
        if not s:
            return None
        # Normalize OCR errors before extracting digits
        normalized = _normalize_ocr_smudge(s)
        nums = re.findall(r'\d{6,}', normalized)
        if not nums:
            nums = re.findall(r'(?:\d\s+){5,}\d', normalized)
            if nums:
                return re.sub(r'\s+', '', nums[0])
            return None
        nums.sort(key=len, reverse=True)
        return nums[0]

    # Flexible patterns allowing OCR errors in numbers
    patterns = [
        r'D[.\s]*[I1L][.\s]*(?:[IL1][.\s]*)?N[O0][.\s]*(?:&\s*DATE)?[:\-\s]*([0-9OIlSs\s]{6,})',
        r'\bD[.\s]*I[.\s]*N[O0][.\s]*[:\-\s]*([0-9OIlSs\s]{6,})',
        r'\bINV(?:OICE)?\s*NO[.\s:]*([A-Z0-9OIlSs\-/\s]{6,})',
        r'Invoice\s*No[^0-9OIlSs]*([0-9OIlSs]{5,})',
    ]
    
    for pat in patterns:
        m = re.search(pat, U, re.IGNORECASE | re.DOTALL)
        if m:
            val = keep_digits(m.group(1))
            if val:
                return val

    # Backup pattern
    m = re.search(r'D[.\s]*[I1L][.\s]*(?:[IL1][.\s]*)?N[O0].{0,30}?([0-9OIlSs]{6,})', U, re.IGNORECASE | re.DOTALL)
    if m:
        extracted = m.group(1)
        normalized = _normalize_ocr_smudge(extracted)
        cleaned = re.sub(r'[^0-9]', '', normalized)
        if len(cleaned) >= 6:
            return cleaned
    
    return None


def extract_lr(text: str) -> Optional[str]:
    """Extract L.R./RR number - ENHANCED for smudged OCR"""
    # Patterns allowing OCR errors in numbers (O, I, l, S)
    patterns = [
        (r'L\.?R\.?.*RR\s*No[:.\s/\\-]*([0-9OIlSs]{2,8})', re.IGNORECASE),
        (r'(?:L\.?R\.?\.?|L\.?R\.?)\s*No[:.\s/\\-]*([0-9OIlSs]{2,8})', re.IGNORECASE),
        (r'RR\s*No[:.\s/\\-]*([0-9OIlSs]{2,8})', re.IGNORECASE),
        (r'\bLR[:.\s-]*([0-9OIlSs]{2,8})', re.IGNORECASE),
    ]
    
    for pattern, flags in patterns:
        m = re.search(pattern, text, flags)
        if m:
            extracted = m.group(1)
            # Normalize OCR errors and clean
            normalized = _normalize_ocr_smudge(extracted)
            cleaned = re.sub(r'[^0-9]', '', normalized)
            if len(cleaned) >= 2:
                return cleaned
    
    return None


def extract_irn(text: str) -> Optional[str]:
    """Extract IRN (Invoice Reference Number) - ENHANCED for smudged OCR"""
    # Allow OCR errors in alphanumeric IRN
    m = re.search(r'IRN[:.\s]*([a-zA-Z0-9OIlSs]+)', text, re.IGNORECASE | re.DOTALL)
    if m:
        extracted = m.group(1).strip()
        # Normalize OCR errors in the IRN
        normalized = _normalize_ocr_smudge(extracted)
        return normalized
    return None


def extract_driver_mobile(text: str) -> Optional[str]:
    """Extract Indian mobile number - ENHANCED for smudged OCR"""
    # Allow OCR errors in mobile number (O, I, l, S)
    m = re.search(r'\b([6-9][0-9OIlSs]{9})\b', text, re.MULTILINE)
    if m:
        extracted = m.group(1)
        # Normalize OCR errors to get proper digits
        normalized = _normalize_ocr_smudge(extracted)
        cleaned = re.sub(r'[^0-9]', '', normalized)
        if len(cleaned) == 10 and cleaned[0] in '6789':
            return cleaned
    return None


def extract_consignee(text: str) -> Optional[str]:
    """Extract consignee company name"""
    header_re = re.compile(
        r'(?:Name\s*(?:&|and)\s*Address\s*of\s*(?:Recipient|Consignee))\s*:?', 
        re.IGNORECASE
    )
    stop_tokens = re.compile(
        r'\b(?:GSTIN|GST|STATE|PLACE\s+OF\s+SUPPLY|PO\s*NO(?:/DATE)?|DATE|EMAIL|MOBILE|PHONE|PAN)\b',
        re.IGNORECASE
    )
    suffix_pat = re.compile(
        r'^(.*?\b(?:PRIVATE\s+LIMITED|PVT\.?\s*LTD|LIMITED|LTD|LLP|LLC|INC|CO\.?))\b',
        re.IGNORECASE
    )
    
    lines = (text or "").splitlines()

    def _is_company_line(s: str) -> bool:
        if not s:
            return False
        U = s.upper().strip()
        if stop_tokens.search(U):
            return False
        if any(k in U for k in ["RECIPIENT", "ADDRESS", "NAME", "CONSIGNEE"]):
            return False
        if re.search(r'\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING|CEMENT|ENGINEERS?)\b', U):
            return True
        if U == s.strip() and 1 <= len(U.split()) <= 6 and len(U) >= 4:
            return True
        letters = re.findall(r'[A-Za-z]', s)
        return bool(letters) and (sum(ch.isalpha() for ch in letters) / len(letters) >= 0.65)

    def _clean_company_line(raw: str) -> Optional[str]:
        s = (raw or "").strip(" :-\t")
        m_stop = stop_tokens.search(s)
        if m_stop:
            s = s[:m_stop.start()].rstrip()
        m = suffix_pat.search(s)
        if m:
            s = m.group(1)
        s = re.split(r'\s+\d[\d\s/\-\.]*', s, maxsplit=1)[0]
        s = re.sub(r'\s{2,}', ' ', s).strip(' ,:-.')
        # extra: collapse duplicated repeated phrase if present (A A)
        s = _collapse_duplicate_phrase(s)
        return s or None

    for idx, line in enumerate(lines):
        m = header_re.search(line)
        if not m:
            continue
        
        # Check inline name
        tail = (line[m.end():] or "").strip(" :-")
        if tail and _is_company_line(tail):
            return _clean_company_line(tail)
        
        # Check next lines
        for j in range(idx + 1, min(idx + 10, len(lines))):
            cand = (lines[j] or "").strip()
            if not cand:
                continue
            if _is_company_line(cand):
                return _clean_company_line(cand)
        break
    
    return None


# -------------------------
# New: Cleaning helpers requested by user
# -------------------------
def clean_destination(raw_dest: Optional[str]) -> Optional[str]:
    """
    Conservative cleaning for Destination field.
    - Removes leading 'DESTINATION' label (case-insensitive).
    - Removes OCR-suffix tokens like 'JESPATCH', 'ESPATCH', 'YESPATCH', 'JES PATCH', 'ES PATCH', 'YES PATCH'.
    - Removes any parenthesis content and parentheses.
    - Removes stray punctuation and unwanted tokens, collapses whitespace.
    - Returns uppercase string or None.
    """
    if not raw_dest:
        return None
    s = raw_dest.strip()

    # 1) Remove leading "DESTINATION" label (e.g. "DESTINATION VILLUPURAM")
    s = re.sub(r'^\s*DESTINATION\b[:\-\s]*', '', s, flags=re.IGNORECASE)

    # 2) Remove anything inside parentheses (including parentheses)
    s = re.sub(r'\([^)]*\)', ' ', s)

    # 3) Remove common OCR suffix garbage that ends with PATCH (handles YESPATCH, JESPATCH, ESPATCH, and spaced variants)
    s = re.sub(r'[\-\.,;:_]*\b[A-Za-z]{0,4}\s*PATCH\b[\-\.,;:_]*', ' ', s, flags=re.IGNORECASE)

    # 4) Remove common OCR noise words that might be attached
    s = re.sub(r'\b(?:JES|YES|ES|JE|YE)\b', ' ', s, flags=re.IGNORECASE)

    # 5) Remove any stray parentheses characters
    s = s.replace('(', ' ').replace(')', ' ')

    # 6) Keep only letters, digits and spaces (destination typically place names); remove stray punctuation
    s = re.sub(r'[^A-Za-z0-9\s]', ' ', s)

    # 7) Collapse whitespace and trim
    s = re.sub(r'\s+', ' ', s).strip()

    if not s:
        return None
    return s.upper()


def clean_consignee(raw_consignee: Optional[str]) -> Optional[str]:
    """
    Cleaning for Consignee:
    - Remove stray '|' characters and other leading junk characters.
    - Collapse whitespace and strip leading/trailing punctuation.
    - Collapse obvious duplication e.g. "X X" or repeated halves.
    """
    if not raw_consignee:
        return None
    s = raw_consignee.strip()
    # drop pipe characters
    s = s.replace('|', ' ')
    # remove common leading junk characters
    s = re.sub(r'^[\s\-\.:,;#\*]+', '', s)
    s = re.sub(r'[\s\-\.:,;#\*]+$', '', s)
    s = re.sub(r'\s{2,}', ' ', s)
    s = s.strip()
    s = _collapse_duplicate_phrase(s)
    return s if s else None


def _collapse_duplicate_phrase(s: str) -> str:
    """
    Heuristic to collapse cases where a name/phrase is duplicated back-to-back.
    Example:
      "Larsen and Toubro Limiited Larsen and Toubro Limiited (Avy" -> "Larsen and Toubro Limiited"
    Strategy:
      - split into words, try to find if first N words repeat immediately.
      - fallback: if the first K words appear again later, keep first occurrence.
    """
    if not s:
        return s
    s = s.strip()
    # remove trailing incomplete parentheses fragments
    s = re.sub(r'\s*\([^)]*$', '', s).strip()
    words = s.split()
    n = len(words)
    if n < 4:
        return s
    # try exact half-repeat
    for half in range(n // 2, 1, -1):
        if n >= 2 * half:
            first = words[:half]
            second = words[half:half*2]
            if [w.lower() for w in first] == [w.lower() for w in second]:
                return " ".join(first)
    # try searching for immediate repeated phrase (first M words repeated somewhere soon after)
    for m in range(min(6, n-1), 1, -1):
        first = " ".join(words[:m]).lower()
        rest_joined = " ".join(words[m:]).lower()
        if rest_joined.startswith(first):
            return " ".join(words[:m])
    # fallback: if any exact duplicated substring appears twice in a row, remove duplicates
    s_norm = re.sub(r'\s+', ' ', s).strip()
    # look for exact substring repeated twice with small separator
    m = re.search(r'(.{8,200}?)\s+\1', s_norm, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return s


# Material Code Patterns
SEP = r'[\s\W]*'
CODE_PATTERNS = [
    ("OPC53", [
        re.compile(rf'O{SEP}P{SEP}C{SEP}[5S]{SEP}3\b', re.IGNORECASE),
        re.compile(rf'OPC{SEP}[5S]{SEP}3\b', re.IGNORECASE),
        re.compile(rf'[5S]{SEP}3{SEP}OPC\b', re.IGNORECASE)
    ]),
    ("OPC43", [
        re.compile(rf'O{SEP}P{SEP}C{SEP}4{SEP}3\b', re.IGNORECASE),
        re.compile(rf'OPC{SEP}4{SEP}3\b', re.IGNORECASE),
        re.compile(rf'4{SEP}3{SEP}OPC\b', re.IGNORECASE)
    ]),
    ("PPC53", [
        re.compile(rf'P{SEP}P{SEP}C{SEP}[5S]{SEP}3\b', re.IGNORECASE),
        re.compile(rf'PPC{SEP}[5S]{SEP}3\b', re.IGNORECASE),
        re.compile(rf'[5S]{SEP}3{SEP}PPC\b', re.IGNORECASE)
    ]),
    ("PPC43", [
        re.compile(rf'P{SEP}P{SEP}C{SEP}4{SEP}3\b', re.IGNORECASE),
        re.compile(rf'PPC{SEP}4{SEP}3\b', re.IGNORECASE),
        re.compile(rf'4{SEP}3{SEP}PPC\b', re.IGNORECASE)
    ]),
    ("OPC", [
        re.compile(rf'O{SEP}P{SEP}C\b', re.IGNORECASE),
        re.compile(r'\bOPC\b', re.IGNORECASE)
    ]),
    ("PPC", [
        re.compile(rf'P{SEP}P{SEP}C\b', re.IGNORECASE),
        re.compile(r'\bPPC\b', re.IGNORECASE)
    ]),
    ("PSC", [
        re.compile(rf'P{SEP}S{SEP}C\b', re.IGNORECASE),
        re.compile(r'\bPSC\b', re.IGNORECASE)
    ]),
    ("SRC", [
        re.compile(rf'S{SEP}R{SEP}C\b', re.IGNORECASE),
        re.compile(r'\bSRC\b', re.IGNORECASE)
    ]),
]


def _merge_split_letters_in_text(t: str) -> str:
    """Merge space-separated letters (O P C → OPC)"""
    t = re.sub(r'(?i)\b([A-Z])\s+([A-Z])\s+([A-Z])\b', r'\1\2\3', t)
    t = re.sub(r'(?i)\b([A-Z])\s+([A-Z])\b', r'\1\2', t)
    return t


def extract_material_code_global(txt: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract cement material code (OPC53, PPC53, etc.)"""
    U = txt.upper().replace('0', 'O').replace('1', 'I').replace('5', 'S')
    U = _merge_split_letters_in_text(U)
    
    best = None
    for code, patterns in CODE_PATTERNS:
        for pat in patterns:
            m = pat.search(U)
            if m:
                idx = m.start()
                if (best is None) or (idx < best[0]):
                    best = (idx, code)
                break
    
    if best:
        return best[1], "global_regex"
    
    squashed = re.sub(r'[^A-Z0-9]+', '', U)
    for code in ["OPC53", "PPC53", "OPC43", "PPC43", "OPC", "PPC", "PSC", "SRC"]:
        if code in squashed:
            return code, "global_squash"
    
    return None, None


def extract_quantity_weight(images: List[Image.Image], text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract quantity/weight - ENHANCED for smudged OCR (e.g., I23.456 MT → 123.456 MT)"""
    # Allow OCR error characters in weight patterns
    num_pat = re.compile(r'\b[0-9OIlSs]+\.[0-9OIlSs]{3}\b')
    
    # Try structured OCR data
    for page in images:
        data = pytesseract.image_to_data(page, output_type=Output.DICT, config="--psm 6")
        n = len(data['text'])
        lines = defaultdict(list)
        
        for i in range(n):
            txt = (data['text'][i] or '').strip()
            if not txt:
                continue
            key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
            l = data['left'][i]
            lines[key].append((txt, l))
        
        for key, wlist in lines.items():
            line_txt = ' '.join([w[0] for w in sorted(wlist, key=lambda z: z[1])])
            if re.search(r'\b(Quantity|Qty)\b', line_txt, re.IGNORECASE):
                (bn, pn, ln) = key
                for offset in range(1, 7):
                    key2 = (bn, pn, ln + offset)
                    if key2 not in lines:
                        continue
                    row_str = ' '.join([w[0] for w in sorted(lines[key2], key=lambda z: z[1])])
                    if '%' in row_str:
                        continue
                    m = num_pat.search(row_str)
                    if m:
                        # Normalize OCR errors in weight
                        normalized = _normalize_ocr_smudge(m.group(0))
                        # Ensure proper decimal format
                        cleaned = re.sub(r'[^0-9.]', '', normalized)
                        if re.match(r'\d+\.\d{3}', cleaned):
                            return cleaned, "quantity_ocr"
    
    # Fallback: Global text search with OCR normalization
    for m in re.finditer(r'\b[0-9OIlSs]+\.[0-9OIlSs]{3}\b', text):
        if '%' not in m.group(0):
            normalized = _normalize_ocr_smudge(m.group(0))
            cleaned = re.sub(r'[^0-9.]', '', normalized)
            if re.match(r'\d+\.\d{3}', cleaned):
                return cleaned, "quantity_global"
    
    return None, None


def _normalize_money(s: str) -> Optional[str]:
    """Normalize currency amount string"""
    if not s:
        return None
    s = s.replace(',', '')
    m = re.search(r'\d+(?:\.\d+)?', s)
    if not m:
        return None
    return f"{float(m.group(0)):.2f}"


def extract_rate(text: str) -> Optional[str]:
    """Extract rate per unit - ENHANCED for smudged OCR (e.g., Rs. 6500/MT, Rs822.ao Per MT)"""
    UNIT = r'(?:MT|M\.?T\.?|TON|TONNE|T|BAG|BAGS|KG|KGS|QUINTAL|QTL|METRIC\s*TON)'
    CURR = r'(?:Rs\.?|₹|INR)\s*'
    # Enhanced amount pattern allowing OCR errors (O, I, l, S, ao)
    AMT = r'([0-9OIlSs]{1,3}(?:,[0-9OIlSs]{2,3})*(?:\.[0-9OIlSsao]+)?|[0-9OIlSs]+(?:\.[0-9OIlSsao]+)?)'
    
    patterns = [
        # Standard patterns
        rf'@\s*{CURR}?{AMT}\s*(?:Per|/)\s*{UNIT}\b',
        rf'(?:Freight|Rate|Price)[^.\n\r]{{0,120}}{CURR}?{AMT}\s*(?:Per|/)\s*{UNIT}\b',
        rf'{CURR}{AMT}\s*(?:Per|/)\s*{UNIT}\b',
        rf'(?:Per|/)\s*{UNIT}\s*[:\-]?\s*{CURR}{AMT}\b',
        rf'\bRate\s*(?:Per|/)\s*{UNIT}\s*[:\-]?\s*{CURR}?{AMT}\b',
        # Enhanced patterns for the specific format in the image
        rf'@\s*{CURR}{AMT}\s*(?:Per|/)\s*{UNIT}',
        rf'Limited\s*@\s*{CURR}{AMT}\s*(?:Per|/)\s*{UNIT}',
        rf'{CURR}{AMT}[.\s]*(?:Per|/)\s*{UNIT}',
        rf'@\s*{CURR}{AMT}[.\s]*(?:ao|oo|OO)\s*(?:Per|/)\s*{UNIT}',
    ]
    
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            amount_str = m.group(1)
            # Normalize OCR errors comprehensively
            amount_str = _normalize_ocr_smudge(amount_str)
            # Additional fixes for common rate OCR errors
            amount_str = amount_str.replace('ao', '00').replace('oo', '00').replace('OO', '00')
            normalized = _normalize_money(amount_str)
            if normalized:
                return normalized
    
    return None


def extract_despatch_city(text: str) -> tuple:
    """
    Extract despatch/source city - searches ENTIRE invoice for city names
    Returns: (city_name or list of cities, count of cities found)
    """
    CANONICAL = [
        "ARAKONAM", "ARAKKONAM", "CHROMPET", "CHENNAI", "TIRUNANIMALI",
        "TIRUNINRAVELI", "VELLORE", "MADURAI", "POONAMALLEE",
        "SRIPERUMBUDUR", "SRIERUMBUDUR"
    ]
    
    found_cities = []
    text_upper = text.upper()
    
    # Search entire invoice text for any canonical city name
    for city in CANONICAL:
        if city in text_upper:
            # Normalize ARAKONAM to ARAKKONAM (with double K)
            normalized = "ARAKKONAM" if city in ("ARAKONAM", "ARAKKONAM") else city
            if normalized not in found_cities:
                found_cities.append(normalized)
    
    # Return (city_name, count)
    if len(found_cities) == 0:
        return None, 0
    elif len(found_cities) == 1:
        return found_cities[0], 1
    else:
        # Multiple cities found - return first one and count
        logger.debug(f"  [Source] Multiple cities found in invoice: {found_cities}")
        return found_cities[0], len(found_cities)


def extract_destination(text: str) -> Optional[str]:
    """Extract destination city"""
    m = re.search(r'Destination\s*[:\-]\s*([^\n\r]+)', text, re.IGNORECASE)
    if m:
        cand = m.group(1)
    else:
        cand = None
        for line in (text or "").splitlines():
            if 'destination' in line.lower():
                cand = line.split(':', 1)[-1].strip()
                break
    
    if not cand:
        return None
    
    cand = re.split(
        r'\b(?:DESPATCH|DISPATCH|FROM|BOOKING|STATION|COMMERCIAL|TERMS)\b',
        cand, 1, flags=re.IGNORECASE
    )[0]
    cand = cand.split('(')[0].strip(" ,:-")
    cand = re.sub(r'[^A-Za-z\s]', ' ', cand)
    cand = re.sub(r'\s+', ' ', cand).strip()
    
    CANONICAL = [
        "ARAKONAM", "CHROMPET", "CHENNAI", "TIRUNINRAVELI",
        "VELLORE", "MADURAI", "POONAMALLEE", "SRIPERUMBUDUR",
        "SRIERUMBUDUR"
    ]
    
    for c in CANONICAL:
        if c in cand.upper():
            return c
    
    lst = get_close_matches(cand.upper(), CANONICAL, n=1, cutoff=0.6)
    return lst[0] if lst else cand.upper() if cand else None


def _normalize_ocr_smudge(text: str) -> str:
    """
    Normalize smudged/mixed OCR characters to their most likely values.
    Handles common OCR errors where characters are partially recognized.
    """
    if not text:
        return text
    
    # Character substitution map for smudged/mixed OCR
    ocr_fixes = {
        'O': '0',  # Letter O to digit 0
        'o': '0',
        'I': '1',  # Letter I to digit 1
        'l': '1',  # Lowercase L to digit 1
        '|': '1',
        'S': '5',  # Letter S to digit 5
        's': '5',
        'Z': '2',  # Letter Z to digit 2
        'z': '2',
        'B': '8',  # Letter B to digit 8
        'g': '9',  # Lowercase g to digit 9
        'q': '9',
        'D': '0',  # Letter D to digit 0 (in some fonts)
        'i': '1',  # Lowercase i to digit 1
    }
    
    result = list(text)
    for i, char in enumerate(result):
        if char in ocr_fixes:
            result[i] = ocr_fixes[char]
    
    return ''.join(result)


def _build_flexible_pattern(keyword: str) -> str:
    r"""
    Build a flexible regex pattern that matches keyword letter-by-letter
    with optional spaces, dots, hyphens between each character.
    Handles smudged/mixed OCR where characters might have extra spacing or punctuation.
    
    Example: "EWB" -> E[\s.-]*W[\s.-]*B
    """
    sep = r'[\s.\-_,|]*'  # Allow spaces, dots, hyphens, underscores, commas, pipes between letters
    return sep.join(list(keyword))


def extract_eway_bill(text: str, ocr_images: Optional[List[Image.Image]] = None) -> Optional[str]:
    r"""
    Extract E-Way Bill number - ENHANCED for smudged/mixed/tilted OCR
    Combines text search + targeted OCR on E-Way Bill region
    Uses letter-by-letter pattern matching to handle smudged characters
    """
    
    # Build flexible patterns using letter-by-letter matching
    ewb_flex = _build_flexible_pattern("EWB")
    eway_flex = _build_flexible_pattern("EWAY")
    way_flex = _build_flexible_pattern("WAY")
    bill_flex = _build_flexible_pattern("BILL")
    
    # Strategy 1: Text-based extraction with FLEXIBLE letter-by-letter patterns
    # NOTE: We search on original text, only normalize the captured numbers
    patterns = [
        # Letter-by-letter flexible patterns for smudged text (allow O, I, l, S in numbers)
        # Most flexible - handles E.W.B., E W B, EWB, etc.
        re.compile(r'E[\s.\-_,|]*W[\s.\-_,|]*B[\s.\-_,|]*(?:No|Number|N[\s.]*o)?\.?\s*[:\-]?\s*([0-9OIlSs|\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\s.\-_,|]*W[\s.\-_,|]*A[\s.\-_,|]*Y[\s.\-_,|]*B[\s.\-_,|]*I[\s.\-_,|]*L[\s.\-_,|]*L\s*(?:No|Number|N[\s.]*o)?\.?\s*[:\-]?\s*([0-9OIlSs|\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\s.\-_,|]*W[\s.\-_,|]*A[\s.\-_,|]*Y\s*(?:No|Number)?\.?\s*[:\-]?\s*([0-9OIlSs|\s]{12,})', re.IGNORECASE),
        # Original strict patterns (for well-formed text)
        re.compile(r'EWB\s*No\.?\s*[:\-]?\s*([0-9\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\s\-]*W[\s\-]*B\s*(?:No|Number)\.?\s*[:\-]?\s*([0-9\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\s\-]*Way\s*Bill\s*(?:No|Number)?\.?\s*[:\-]?\s*([0-9\s]{12,})', re.IGNORECASE),
    ]
    
    # Try patterns on original text first (don't normalize full text - that would change B->8, o->0 in keywords!)
    for pat in patterns:
        m = pat.search(text or "")
        if m:
            # Clean and normalize ONLY the extracted number
            num = m.group(1)
            # Normalize OCR errors in the number (O->0, I->1, l->1, S->5, etc.)
            num = _normalize_ocr_smudge(num)
            # Then remove all non-digits
            num = re.sub(r'[^0-9]', '', num)
            
            # E-Way Bill numbers are EXACTLY 12 digits
            if len(num) == 12 and num.isdigit():
                # Additional validation: should not be all same digit
                if len(set(num)) > 3:  # At least 4 different digits
                    logger.debug(f"  [E-Way] Found via text pattern: {num}")
                    return num
    
    # Strategy 2: Line-by-line search with STRICT context
    lines = (text or "").splitlines()
    for i, line in enumerate(lines):
        # Look for lines with EWB/E-Way keywords
        if re.search(r'(?:E-?Way|EWB)\s*(?:No|Number)?', line, re.IGNORECASE):
            logger.debug(f"  [E-Way] Found keyword in line: {line[:100]}")
            
            # First, try to extract from the same line
            # Look for exactly 12 consecutive digits
            same_line_match = re.search(r'\b([0-9]{12})\b', line)
            if same_line_match:
                candidate = same_line_match.group(1)
                # Validate it's not a date (dates have patterns like 20251104 or similar)
                if not _looks_like_datetime(candidate):
                    logger.debug(f"  [E-Way] Found in same line: {candidate}")
                    return candidate
            
            # Try with spaces removed from the line
            cleaned_line = re.sub(r'[^0-9]', '', line)
            if len(cleaned_line) >= 12:
                # Look for 12-digit sequence
                for j in range(len(cleaned_line) - 11):
                    candidate = cleaned_line[j:j+12]
                    if not _looks_like_datetime(candidate) and len(set(candidate)) > 3:
                        logger.debug(f"  [E-Way] Found in cleaned line: {candidate}")
                        return candidate
            
            # Then check nearby lines (within 2 lines)
            search_context = ' '.join(lines[max(0, i):min(len(lines), i+3)])
            numbers = re.findall(r'\b([0-9]{12})\b', search_context)
            for num in numbers:
                if not _looks_like_datetime(num) and len(set(num)) > 3:
                    logger.debug(f"  [E-Way] Found via line context: {num}")
                    return num
    
    # Strategy 3: OCR-based extraction from E-Way Bill region (for tilted images)
    if ocr_images:
        logger.debug("  [E-Way] Attempting targeted OCR on E-Way Bill region...")
        for img_idx, img in enumerate(ocr_images):
            try:
                # OPTIMIZED: Try fewer angles with early exit on success
                # Reduced from 9 angles to 5 most common ones
                rotation_angles = [0, -10, 10, -5, 5]  # Most common tilt angles first
                
                for angle in rotation_angles:
                    try:
                        # Rotate the entire image
                        if angle != 0:
                            rotated_img = img.rotate(angle, expand=True, fillcolor='white')
                            logger.debug(f"  [E-Way] Trying rotation: {angle} degrees")
                        else:
                            rotated_img = img
                        
                        # Try to find and crop the E-Way Bill region from rotated image
                        eway_crop = _extract_eway_region(rotated_img)
                        if eway_crop:
                            # OPTIMIZED: Reduce preprocessing variants from 5+ to 2 most effective
                            variants = _preprocess_for_eway(eway_crop)
                            # Only use first 2 variants (high contrast + one threshold)
                            variants = variants[:2] if len(variants) > 2 else variants
                            
                            for variant_idx, variant in enumerate(variants):
                                # OPTIMIZED: Try only PSM 6 first (fastest and most accurate for blocks)
                                # Only try PSM 7 if PSM 6 fails
                                psm_modes = [6, 7] if angle == 0 else [6]  # Fewer modes for rotated
                                
                                for psm in psm_modes:
                                    try:
                                        # OPTIMIZED: Try digits-only first (faster than full text)
                                        config_digits = f"--oem 1 --psm {psm} -c tessedit_char_whitelist=0123456789"
                                        eway_text = pytesseract.image_to_string(variant, config=config_digits, lang="eng")
                                        
                                        # Extract exactly 12-digit number
                                        numbers = re.findall(r'\b([0-9]{12})\b', eway_text)
                                        for num in numbers:
                                            if not _looks_like_datetime(num) and len(set(num)) > 3:
                                                logger.debug(f"  [E-Way] ✓ Found via targeted OCR at {angle}°: {num}")
                                                return num
                                        
                                        # Try sequences in cleaned text
                                        cleaned = re.sub(r'[^0-9]', '', eway_text)
                                        if len(cleaned) >= 12:
                                            for j in range(len(cleaned) - 11):
                                                candidate = cleaned[j:j+12]
                                                if not _looks_like_datetime(candidate) and len(set(candidate)) > 3:
                                                    logger.debug(f"  [E-Way] ✓ Found via sequence at {angle}°: {candidate}")
                                                    return candidate
                                        
                                        # Only try full text OCR if digits-only failed AND this is angle 0
                                        if angle == 0:
                                            config = f"--oem 1 --psm {psm}"
                                            eway_text_full = pytesseract.image_to_string(variant, config=config, lang="eng")
                                            
                                            # Look for EWB pattern with context
                                            ewb_patterns = [
                                                r'(?:EWB|E\s*W\s*B)\s*(?:No|Number)?\.?\s*[:\-]?\s*([0-9\s]{12,18})',
                                                r'(?:E[\s\-]*Way)\s*(?:No|Number)?\.?\s*[:\-]?\s*([0-9\s]{12,18})',
                                            ]
                                            
                                            for pat in ewb_patterns:
                                                ewb_match = re.search(pat, eway_text_full, re.IGNORECASE | re.DOTALL)
                                                if ewb_match:
                                                    num = re.sub(r'[^0-9]', '', ewb_match.group(1))
                                                    if len(num) == 12 and not _looks_like_datetime(num) and len(set(num)) > 3:
                                                        logger.debug(f"  [E-Way] ✓ Found via EWB pattern at {angle}°: {num}")
                                                        return num
                                                    
                                    except Exception as e:
                                        logger.debug(f"  [E-Way] OCR at {angle}° PSM {psm} failed: {e}")
                                        continue
                    except Exception as e:
                        logger.debug(f"  [E-Way] Rotation {angle}° failed: {e}")
                        continue
                
                # REMOVED: Full page deskewing (too slow, rarely needed after angle attempts)
            except Exception as e:
                logger.debug(f"  [E-Way] Image processing failed: {e}")
                continue
    
    # Strategy 4: Smart Fallback - VERY SELECTIVE
    # Only look for 12-digit numbers that are clearly E-Way Bills
    all_12digit = re.findall(r'\b([0-9]{12})\b', text or "")
    candidates = []
    
    for num in all_12digit:
        # Skip if it looks like a datetime
        if _looks_like_datetime(num):
            logger.debug(f"  [E-Way] Skipping datetime-like number: {num}")
            continue
        
        # E-Way Bills typically start with 1, 3, 5, 7, 8, 9 (NOT 2 which is common in dates)
        if num[0] not in '2' and len(set(num)) > 3:
            candidates.append(num)
    
    if candidates:
        # Prefer numbers starting with 5, 1, 3 (most common for E-Way Bills)
        priority = [n for n in candidates if n[0] in '513']
        if priority:
            logger.debug(f"  [E-Way] Found via fallback (priority): {priority[0]}")
            return priority[0]
        
        logger.debug(f"  [E-Way] Found via fallback: {candidates[0]}")
        return candidates[0]
    
    logger.debug("  [E-Way] No E-Way Bill number found")
    return None


def _looks_like_datetime(num: str) -> bool:
    """
    Check if a 12-digit number looks like a datetime stamp
    Common patterns: 
    - 201020252359 (DDMMYYYYHHMM)
    - 205102025235 (variations with year 2025, 2020, etc.)
    - 510202523590 (MMDDYYYYHHMM - month first)
    """
    if len(num) != 12:
        return False
    
    # Check for date-like patterns in multiple formats
    
    # Format 1: DDMMYYYYHHMM (day first)
    try:
        d = int(num[0:2])
        m = int(num[2:4])
        y = int(num[4:8])
        h = int(num[8:10])
        min_val = int(num[10:12])
        
        if (1 <= d <= 31 and 1 <= m <= 12 and 2020 <= y <= 2030 and 
            0 <= h <= 23 and 0 <= min_val <= 59):
            return True
    except ValueError:
        pass
    
    # Format 2: MMDDYYYYHHMM (month first - like 510202523590)
    try:
        m = int(num[0:2])
        d = int(num[2:4])
        y = int(num[4:8])
        h = int(num[8:10])
        min_val = int(num[10:12])
        
        if (1 <= m <= 12 and 1 <= d <= 31 and 2020 <= y <= 2030 and 
            0 <= h <= 23 and 0 <= min_val <= 59):
            return True
    except ValueError:
        pass
    
    # Format 3: YYYYMMDDHHSS (year first)
    try:
        y = int(num[0:4])
        m = int(num[4:6])
        d = int(num[6:8])
        h = int(num[8:10])
        s = int(num[10:12])
        
        if (2020 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31 and 
            0 <= h <= 23 and 0 <= s <= 59):
            return True
    except ValueError:
        pass
    
    # Check for year pattern (2025, 2024, etc.) appearing in the number
    if '2025' in num or '2024' in num or '2023' in num or '2026' in num or '2020' in num:
        # If it contains a recent year, it's likely a datetime
        return True
    
    # Check for repeated patterns like 202020202020
    if len(set(num)) <= 3:
        return True
    
    # Check if it has too many sequential digits (like 123456789012)
    sequential = sum(1 for i in range(len(num)-1) if abs(int(num[i]) - int(num[i+1])) <= 1)
    if sequential >= 8:
        return True
    
    # Check for hour:minute patterns (23:59 → 2359)
    # Common times: 2359, 2330, 0000, 1200, etc.
    last_four = num[8:12]
    try:
        h = int(last_four[0:2])
        m = int(last_four[2:4])
        # If last 4 digits look like HH:MM, it's probably datetime
        if 0 <= h <= 23 and 0 <= m <= 59:
            # Also check if the middle portion looks like a year
            middle_four = num[4:8]
            if middle_four.startswith('202'):  # Years 2020-2029
                return True
    except ValueError:
        pass
    
    return False


def _extract_eway_region(img: Image.Image) -> Optional[Image.Image]:
    """Extract the region likely to contain E-Way Bill number (top-left area)"""
    try:
        w, h = img.size
        # E-Way Bill is typically in the top-left corner
        # Crop roughly top 15% and left 50% of the image
        crop_box = (0, 0, int(w * 0.5), int(h * 0.15))
        eway_region = img.crop(crop_box)
        return eway_region
    except Exception as e:
        logger.debug(f"  [E-Way] Region extraction failed: {e}")
        return None


def _deskew_image(img: Image.Image) -> Image.Image:
    """Deskew/rotate tilted image to horizontal orientation"""
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV
        cv_img = np.array(img.convert("L"))
        
        # Threshold
        _, binary = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Detect text angle using minAreaRect
        coords = cv2.findNonZero(binary)
        if coords is not None and len(coords) > 10:
            angle = cv2.minAreaRect(coords)[-1]
            
            # Adjust angle
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
            
            # Only rotate if angle is significant (> 0.5 degrees)
            if abs(angle) > 0.5:
                logger.debug(f"  [E-Way] Deskewing image by {angle:.2f} degrees")
                h, w = cv_img.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(cv_img, M, (w, h), 
                                        flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
                return Image.fromarray(rotated)
        
        return img
    except ImportError:
        logger.debug("  [E-Way] OpenCV not available, skipping deskew")
        return img
    except Exception as e:
        logger.debug(f"  [E-Way] Deskew failed: {e}")
        return img


def _preprocess_for_eway(img: Image.Image) -> List[Image.Image]:
    """Aggressive preprocessing specifically for E-Way Bill OCR on tilted images"""
    variants = []
    
    try:
        # FIRST: Try to deskew the image if it's tilted
        deskewed = _deskew_image(img)
        
        # Convert to grayscale
        gray = deskewed.convert("L")
        
        # Variant 1: High contrast
        contrast = ImageOps.autocontrast(gray, cutoff=2)
        variants.append(contrast)
        
        # Variant 2: Inverted (sometimes helps with dark backgrounds)
        inverted = ImageOps.invert(contrast)
        variants.append(inverted)
        
        # Variant 3: Threshold
        try:
            import cv2
            import numpy as np
            
            cv_img = np.array(gray)
            
            # Binary threshold
            _, binary = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            variants.append(Image.fromarray(binary))
            
            # Adaptive threshold
            adaptive = cv2.adaptiveThreshold(cv_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                            cv2.THRESH_BINARY, 11, 2)
            variants.append(Image.fromarray(adaptive))
            
            # Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            variants.append(Image.fromarray(morph))
            
        except ImportError:
            # If OpenCV not available, use PIL operations
            # Simple threshold
            threshold = gray.point(lambda x: 0 if x < 128 else 255, '1')
            variants.append(threshold.convert('L'))
        
        # Variant 4: Upscaled (better OCR on small text)
        scale_factor = 2
        upscaled = gray.resize((gray.width * scale_factor, gray.height * scale_factor), Image.LANCZOS)
        variants.append(ImageOps.autocontrast(upscaled))
        
    except Exception as e:
        logger.debug(f"  [E-Way] Preprocessing failed: {e}")
        # Return original if preprocessing fails
        variants = [img.convert("L")]
    
    return variants


def extract_eway_expiry(text: str) -> Optional[str]:
    """Extract E-Way Bill expiry date/time - ENHANCED for smudged/mixed OCR"""
    
    # Build flexible letter-by-letter patterns (but DON'T normalize full text)
    ewb_flex = _build_flexible_pattern("EWB")
    eway_flex = _build_flexible_pattern("EWAY")
    valid_flex = _build_flexible_pattern("VALID")
    exp_flex = _build_flexible_pattern("EXP")
    
    # Enhanced date-time pattern that handles OCR errors in digits
    # Allows O, I, l, S mixed with digits
    datetime_pat = r'([0-9OIlSs]{1,2}[./-][0-9OIlSs]{1,2}[./-][0-9OIlSs]{2,4}\s+[0-9OIlSs]{1,2}:[0-9OIlSs]{2}(?::[0-9OIlSs]{2})?)'
    
    patterns = [
        # Flexible letter-by-letter patterns for smudged text
        r'E[\s.\-_,|]*W[\s.\-_,|]*B\s*(?:Exp|Expiry)\.?\s*[:\-]?\s*' + datetime_pat,
        r'E[\s.\-_,|]*W[\s.\-_,|]*A[\s.\-_,|]*Y[\s.\-_,|]*B[\s.\-_,|]*I[\s.\-_,|]*L[\s.\-_,|]*L\s*(?:Valid(?:ity)?|Valid\s*Upto)?\s*[:\-]?\s*' + datetime_pat,
        r'V[\s.\-_,|]*A[\s.\-_,|]*L[\s.\-_,|]*I[\s.\-_,|]*D\s*(?:Till|Upto|Until)?\s*[:\-]?\s*' + datetime_pat,
        r'Valid(?:ity)?\s*[:\-]?\s*' + datetime_pat,
        # Standard patterns for well-formed text
        r'(?:E-?Way\s*Bill\s*(?:Validity|Valid\s*Upto|Exp(?:iry)?)\s*[:\-]?\s*)([0-9OIlSs./-]+\s+[0-9OIlSs:]{4,})',
        r'(?:EWB\s*Exp\.\s*[:\-]?\s*)([0-9OIlSs./-]+\s+[0-9OIlSs:]{4,})',
        r'(?:Valid\s*(?:Till|Upto|Until)\s*[:\-]?\s*)([0-9OIlSs./-]+\s+[0-9OIlSs:]{4,})',
        r'(?:Expires?\s*(?:On|At)?\s*[:\-]?\s*)([0-9OIlSs./-]+\s+[0-9OIlSs:]{4,})',
    ]
    
    # Try on original text (don't normalize full text - only normalize captured dates)
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE | re.DOTALL)
        if match:
            expiry = match.group(1).strip()
            # Normalize any OCR errors in the extracted date-time
            expiry = _normalize_ocr_smudge(expiry)
            logger.debug(f"  [E-Way Expiry] Found via pattern: {expiry}")
            return expiry
    
    # Look for date-time patterns in lines containing E-Way keywords
    datetime_pattern = re.compile(datetime_pat)
    
    lines = (text or "").splitlines()
    for line in lines:
        # Check if line contains E-Way/validity keywords (flexible matching)
        if re.search(r'(?:e[\s.\-]*w[\s.\-]*[ab]|valid|expiry|expires)', line, re.IGNORECASE):
            match = datetime_pattern.search(line)
            if match:
                expiry = match.group(1).strip()
                # Normalize OCR errors
                expiry = _normalize_ocr_smudge(expiry)
                logger.debug(f"  [E-Way Expiry] Found in keyword line: {expiry}")
                return expiry
    
    # Fallback: Look for any date-time pattern near "valid" or "exp" keywords
    simple_datetime = re.compile(r'([0-9OIlSs]{1,2}[./-][0-9OIlSs]{1,2}[./-][0-9OIlSs]{2,4}\s+[0-9OIlSs]{1,2}:[0-9OIlSs]{2})')
    for line in lines:
        if re.search(r'\b(valid|exp|till|upto)', line, re.IGNORECASE):
            match = simple_datetime.search(line)
            if match:
                expiry = match.group(1).strip()
                expiry = _normalize_ocr_smudge(expiry)
                logger.debug(f"  [E-Way Expiry] Found near keyword: {expiry}")
                return expiry
    
    logger.debug("  [E-Way Expiry] NOT FOUND")
    return None


# -------------------------
# ENHANCED VEHICLE EXTRACTOR - FIXED VERSION
# -------------------------
def _cleanup_plate_token(tok: str) -> str:
    """Cleanup OCR tokens to form a vehicle plate."""
    if not tok:
        return tok
    s = tok.upper()
    # Remove common OCR punctuation/artifacts but keep alphanumeric
    s = re.sub(r'[^A-Z0-9]', '', s)
    return s

def _normalize_vehicle_ocr_errors(plate: str) -> str:
    """Normalize common OCR errors in vehicle plates - ENHANCED"""
    if not plate:
        return plate
    
    # First apply general OCR normalization
    normalized = _normalize_ocr_smudge(plate.upper())
    
    # Handle specific vehicle number patterns that indicate OCR errors
    # Pattern: KA + O/L + LANO -> KA + 01 + AN  
    if len(normalized) >= 10:
        # Check if it looks like KA[OL]LANO pattern
        match = re.match(r'^([A-Z]{2})([0-9])([A-Z]{1,4})([0-9]{3,4})$', normalized)
        if match:
            state = match.group(1)
            digit = match.group(2)
            letters = match.group(3)
            numbers = match.group(4)
            
            # Try to extract proper letter sequence (usually 2-3 chars)
            if len(letters) > 3:
                # For patterns like "1ANO" or "0ANL", extract middle letters
                if letters[0] in '0123456789':
                    # First char is likely a digit OCR error
                    digit = digit + letters[0]
                    letters = letters[1:3]
                else:
                    letters = letters[:2]
            
            result = f"{state}{digit}{letters}{numbers}"
            if result != plate.upper():
                logger.debug(f"  [Vehicle] OCR normalization: {plate} -> {result}")
            return result
    
    # Standard pattern normalization
    if len(normalized) >= 8:
        match = re.match(r'^([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{3,4})$', normalized)
        if match:
            return normalized
    
    return normalized


def extract_vehicle(text: str, ocr_images: Optional[List[Image.Image]] = None) -> Optional[str]:
    """
    ENHANCED VEHICLE EXTRACTOR - Specifically designed to extract from 
    "Vehicle No./Wagon NO.: KA01AN0922" format
    
    Strategy:
    1. Look for explicit "Vehicle No." or "Wagon NO." labels
    2. Extract the alphanumeric value immediately following the label
    3. Validate against Indian vehicle number patterns
    """
    
    # Primary patterns for explicit vehicle number labels
    VEHICLE_LABEL_PATTERNS = [
        # Standard patterns - Match "Vehicle No./Wagon NO.: KA01AN0922" or similar variations
        re.compile(r'Vehicle\s*No\.?\s*/?\s*Wagon\s*NO?\.?\s*[:\-]?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Vehicle\s*No\.?\s*[:\-/]?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Wagon\s*NO?\.?\s*[:\-/]?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})', re.IGNORECASE),
        # With spaces in the vehicle number
        re.compile(r'Vehicle\s*No\.?\s*/?\s*Wagon\s*NO?\.?\s*[:\-]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Vehicle\s*No\.?\s*[:\-/]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Wagon\s*NO?\.?\s*[:\-/]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', re.IGNORECASE),
        # OCR error patterns - Handle cases like KAOLANO0922
        re.compile(r'Vehicle\s*No\.?\s*/?\s*Wagon\s*NO?\.?\s*[:\-]?\s*([A-Z]{2}[OL0-9]{1,2}[A-Z]{1,4}[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Vehicle\s*No\.?\s*[:\-/]?\s*([A-Z]{2}[OL0-9]{1,2}[A-Z]{1,4}[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Wagon\s*NO?\.?\s*[:\-/]?\s*([A-Z]{2}[OL0-9]{1,2}[A-Z]{1,4}[0-9]{3,4})', re.IGNORECASE),
    ]
    
    # Robust plate validation patterns
    PLATE_PATTERNS = [
        re.compile(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$', re.IGNORECASE), # KA01AN0922, TN23DA8502
        re.compile(r'^[A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4}$',re.IGNORECASE),# With spaces
        # Handle OCR errors where digits might be read as letters (like O for 0, L for 1)
        re.compile(r'^[A-Z]{2}[OL0-9]{1,2}[A-Z]{1,4}[0-9]{3,4}$', re.IGNORECASE), # KAOLANO0922 style OCR errors
    ]
    
    def _is_valid_vehicle_plate(plate: str) -> bool:
        """Validate if string matches Indian vehicle number format"""
        if not plate:
            return False
        clean = _cleanup_plate_token(plate)
        if len(clean) < 8 or len(clean) > 12:  # Allow longer plates for OCR errors
            return False
        
        # Try direct match first
        for pat in PLATE_PATTERNS:
            if pat.match(clean):
                return True
        
        # Try with OCR error normalization
        normalized = _normalize_vehicle_ocr_errors(clean)
        if normalized != clean:
            for pat in PLATE_PATTERNS[:2]:  # Use stricter patterns for normalized text
                if pat.match(normalized):
                    return True
        
        return False
    # STRATEGY 1: Search for labeled vehicle numbers in text
    logger.info("  [Vehicle] Strategy 1: Searching for labeled patterns...")
    for pattern in VEHICLE_LABEL_PATTERNS:
        matches = pattern.finditer(text)
        for match in matches:
            candidate = match.group(1)
            if _is_valid_vehicle_plate(candidate):
                clean = _cleanup_plate_token(candidate)
                normalized = _normalize_vehicle_ocr_errors(clean)
                result = normalized if normalized != clean else clean
                logger.info(f"  [Vehicle] ✓ Found via labeled pattern: {result}")
                return result
    
    # STRATEGY 2: Use structured OCR to find lines with vehicle labels
    if ocr_images:
        logger.info("  [Vehicle] Strategy 2: Using structured OCR...")
        for img_idx, img in enumerate(ocr_images):
            try:
                data = pytesseract.image_to_data(img, output_type=Output.DICT, config="--psm 6", lang="eng")
            except Exception as e:
                logger.debug(f"  [Vehicle] OCR failed on image {img_idx}: {e}")
                continue
            
            n = len(data.get('text', []))
            lines = defaultdict(list)
            
            # Group words into lines
            for i in range(n):
                txt = (data['text'][i] or '').strip()
                if not txt:
                    continue
                k = (data.get('block_num', [0])[i], data.get('par_num', [0])[i], data.get('line_num', [0])[i])
                left = data.get('left', [0])[i]
                lines[k].append((left, txt))
            
            ordered_keys = sorted(lines.keys(), key=lambda k: (k[0], k[1], k[2]))
            
            for idx, k in enumerate(ordered_keys):
                row = " ".join(w for _, w in sorted(lines[k], key=lambda x: x[0]))
                
                # Check if line contains vehicle label
                if re.search(r'\b(vehicle|wagon)\b', row, re.IGNORECASE):
                    logger.info(f"  [Vehicle] Found label line: {row[:100]}")
                    
                    # Try to extract from same line
                    for pattern in VEHICLE_LABEL_PATTERNS:
                        match = pattern.search(row)
                        if match:
                            candidate = match.group(1)
                            if _is_valid_vehicle_plate(candidate):
                                clean = _cleanup_plate_token(candidate)
                                normalized = _normalize_vehicle_ocr_errors(clean)
                                result = normalized if normalized != clean else clean
                                logger.info(f"  [Vehicle] ✓ Found via OCR same-line: {result}")
                                return result
                    
                    # Check next 2 lines
                    for offset in (1, 2):
                        if idx + offset < len(ordered_keys):
                            k2 = ordered_keys[idx + offset]
                            row2 = " ".join(w for _, w in sorted(lines[k2], key=lambda x: x[0]))
                            logger.info(f"  [Vehicle] Checking next line: {row2[:100]}")
                            
                            # Look for vehicle pattern in next line (including OCR errors)
                            plate_patterns = [
                                r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})',  # Standard
                                r'([A-Z]{2}[OL0-9]{1,2}[A-Z]{1,4}[0-9]{3,4})',  # OCR errors
                            ]
                            for pattern in plate_patterns:
                                plate_search = re.search(pattern, row2, re.IGNORECASE)
                                if plate_search:
                                    candidate = plate_search.group(1)
                                    if _is_valid_vehicle_plate(candidate):
                                        clean = _cleanup_plate_token(candidate)
                                        normalized = _normalize_vehicle_ocr_errors(clean)
                                        result = normalized if normalized != clean else clean
                                        logger.info(f"  [Vehicle] ✓ Found via OCR next-line: {result}")
                                        return result
    
    # STRATEGY 3: Conservative global search (last resort)
    logger.info("  [Vehicle] Strategy 3: Conservative global search...")
    # Broader pattern to catch OCR errors like KAOLANO0922
    global_patterns = [
        re.compile(r'\b([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})\b', re.IGNORECASE),  # Standard
        re.compile(r'\b([A-Z]{2}[OL0-9]{1,2}[A-Z]{1,4}[0-9]{3,4})\b', re.IGNORECASE),  # OCR errors
    ]
    
    candidates = []
    for line in text.splitlines():
        for pattern in global_patterns:
            for match in pattern.finditer(line):
                candidate = match.group(1)
                # Filter out PO-like tokens (L23M727, LE23M727)
                if re.match(r'^[LEI]\d', candidate, re.IGNORECASE):
                    continue
                if _is_valid_vehicle_plate(candidate):
                    clean = _cleanup_plate_token(candidate)
                    normalized = _normalize_vehicle_ocr_errors(clean)
                    result = normalized if normalized != clean else clean
                    candidates.append(result)
    
    if candidates:
        # Remove duplicates while preserving order
        candidates = list(dict.fromkeys(candidates))
        
        # Prefer Indian state codes (KA, TN, MH, etc.)
        indian_states = [c for c in candidates if re.match(r'^(KA|TN|MH|DL|UP|RJ|GJ|AP|TS|KL|PB|HR)', c)]
        if indian_states:
            result = indian_states[0]
            logger.info(f"  [Vehicle] ✓ Found via global search: {result}")
            return result
        
        result = candidates[0]
        logger.info(f"  [Vehicle] ✓ Found via global search: {result}")
        return result
    
    logger.info("  [Vehicle] ✗ No valid vehicle number found")
    return None


# -------------------------
# Main Extraction Runner
# -------------------------
def run(
    pdf_path: str,
    *,
    tesseract_cmd: Optional[str] = None,
    poppler_path: Optional[str] = None,
    save_raw_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Two-Pass Extraction Architecture:
    
    PASS 1 (This function):
    - Render PDF at DPI 600
    - Run Tesseract OCR for ALL fields EXCEPT Delivery Address
    
    PASS 2 (delivery_address.py):
    - Focused PaddleOCR scan for Delivery Address only
    
    Returns: Complete RAW data dictionary with all fields
    """
    
    # ============================================
    # SETUP: Detect Tesseract and Poppler
    # ============================================
    tess = _detect_tesseract(tesseract_cmd)
    logger.info("✓ Using Tesseract: %s", tess)
    
    poppler = _detect_poppler(poppler_path)
    if poppler:
        logger.info("✓ Using Poppler: %s", poppler)

    # ============================================
    # PASS 1: Render PDF and Run Tesseract OCR
    # ============================================
    logger.info("=" * 60)
    logger.info("PASS 1: Tesseract OCR @ DPI 300 (Optimized for speed)")
    logger.info("=" * 60)
    
    try:
        # OPTIMIZED: Reduced DPI from 600 to 300 for 4x faster rendering
        # DPI 300 is still excellent quality for text OCR
        if poppler:
            pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler)
        else:
            pages = convert_from_path(pdf_path, dpi=300)
        logger.info("✓ Rendered %d page(s) from PDF", len(pages))
    except Exception as e:
        if platform.system() == "Windows":
            raise RuntimeError(
                f"Failed to render PDF: {e}\n"
                "Install Poppler for Windows and set POPPLER_PATH environment variable."
            )
        raise

    # Run OCR on all pages
    all_blocks: List[str] = []
    originals: List[Image.Image] = []
    
    for pg_num, pg in enumerate(pages, 1):
        logger.info("  Processing page %d...", pg_num)
        originals.append(pg)
        
        variants = _preprocess_variants_fast(pg)
        page_texts: List[str] = []
        
        for v in variants:
            page_texts.extend(_ocr_configs_fast(v))
        
        merged = _merge_text(page_texts) if page_texts else ""
        all_blocks.append(merged)

    # Combine all page text
    text = "\n".join(all_blocks)
    logger.info("✓ OCR completed. Total text length: %d characters", len(text))

    # ============================================
    # EXTRACT FIELDS (All except Delivery Address)
    # ============================================
    logger.info("\nExtracting fields from OCR text...")
    
    invoice_no = extract_invoice_no(text)
    logger.info("  Invoice No: %s", invoice_no or "NOT FOUND")
    
    invoice_date = extract_invoice_date(text, invoice_no)
    logger.info("  Invoice Date: %s", invoice_date or "NOT FOUND")
    
    lr_no = extract_lr(text)
    logger.info("  L.R. No: %s", lr_no or "NOT FOUND")
    
    consignee = extract_consignee(text)
    consignee = clean_consignee(consignee)
    logger.info("  Consignee: %s", consignee or "NOT FOUND")
    
    consignor = "UltraTech Cement Limited" if "ULTRATECH CEMENT LIMITED" in (text or "").upper() else None
    logger.info("  Consignor: %s", consignor or "NOT FOUND")
    
    weight, weight_method = extract_quantity_weight(originals, text)
    logger.info("  Weight: %s (method: %s)", weight or "NOT FOUND", weight_method or "N/A")
    
    content_name, content_method = extract_material_code_global(text)
    if not content_name:
        content_name = (
            find_value(r'Name\s*of\s*Commodity\s*[:\-]\s*([A-Za-z0-9 /-]+)', text) or
            find_value(r'Description\s*of\s*Goods\s*[:\-]\s*([A-Za-z0-9 /-]+)', text)
        )
    logger.info("  Content Name: %s", content_name or "NOT FOUND")
    
    rate = extract_rate(text)
    if not rate:
        # Debug: Check if we can find any rate-like patterns
        rate_debug_patterns = [r'@.*?Rs.*?[0-9]+.*?MT', r'Rs.*?[0-9]+.*?(?:Per|/).*?MT']
        for pattern in rate_debug_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                logger.debug("  [Rate Debug] Found rate-like patterns: %s", matches[:3])
                break
    logger.info("  Rate: %s", rate or "NOT FOUND")
    
    despatch_city, city_count = extract_despatch_city(text)
    logger.info("  Despatch City: %s (found %d cities in invoice)", despatch_city or "NOT FOUND", city_count)
    
    destination = extract_destination(text)
    destination = clean_destination(destination)
    logger.info("  Destination: %s", destination or "NOT FOUND")
    
    eway_no = extract_eway_bill(text, originals)  # Pass images for enhanced OCR
    if not eway_no:
        # Debug: Check if we can find any E-Way Bill-like patterns
        eway_debug = re.findall(r'(?:E-?Way|EWB).*?[0-9]{8,}', text, re.IGNORECASE)
        if eway_debug:
            logger.debug("  [E-Way Debug] Found E-Way-like patterns: %s", eway_debug[:3])
    logger.info("  E-Way Bill No: %s", eway_no or "NOT FOUND")
    
    eway_expiry = extract_eway_expiry(text)
    if not eway_expiry:
        # Debug: Check for date-time patterns
        datetime_debug = re.findall(r'[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}\s+[0-9]{1,2}:[0-9]{2}', text)
        if datetime_debug:
            logger.debug("  [E-Way Expiry Debug] Found datetime patterns: %s", datetime_debug[:3])
    logger.info("  E-Way Bill Expiry: %s", eway_expiry or "NOT FOUND")
    
    # Vehicle extraction with enhanced function and structured OCR
    vehicle_no = extract_vehicle(text, originals)
    logger.info("  Vehicle No: %s", vehicle_no or "NOT FOUND")
    
    irn = extract_irn(text)
    logger.info("  IRN: %s", irn or "NOT FOUND")
    
    driver_mobile = extract_driver_mobile(text)
    logger.info("  Driver Mobile: %s", driver_mobile or "NOT FOUND")
    
    goods_type = "BAG" if re.search(r'\bBAGS?\b', text, re.IGNORECASE) else (
        "BULK" if re.search(r'\bBULK\b', text, re.IGNORECASE) else None
    )
    logger.info("  Goods Type: %s", goods_type or "NOT DETECTED")

    # ============================================
    # BUILD RAW DATA (WITHOUT Delivery Address)
    # ============================================
    
    # Determine GST Type: if 2 or 3 cities found, set as "Unregistered"
    gst_type = "Unregistered" if city_count in (2, 3) else None
    
    raw_data: Dict[str, Any] = {
        "Consignment No": lr_no,
        "Source": despatch_city,  # Will be "ARAKKONAM" if ARAKONAM/ARAKKONAM found in invoice
        "Destination": destination,
        "E-Way Bill No": eway_no,
        "E-Way Bill Date": invoice_date,
        "E-Way Bill Valid Upto": eway_expiry,
        "Consignor": consignor,
        "Consignee": consignee,
        "Billing Party": consignee,
        "Delivery Address": None,  # Will be filled by PASS 2
        "Vehicle": vehicle_no,
        "Driver Mobile": driver_mobile,
        "Date (ERP entry date)": invoice_date,
        "Invoice No": invoice_no,
        "Invoice Date": invoice_date,
        "Content Name (Goods Name)": content_name,
        "Actual Weight": weight,
        "E-Way Bill No (Goods)": eway_no,
        "Rate": rate,
        "IRN": irn,
        "GST Type": "Unregistered",  # "Unregistered" if 2 or 3 cities found, else None
        "goods_type": goods_type,
    }

    # ============================================
    # PASS 2: Call Delivery Address Extractor
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("PASS 2: PaddleOCR Focused Scan (Delivery Address Only)")
    logger.info("=" * 60)
    
    if not _HAS_DELIVERY_EXTRACTOR:
        logger.warning("⚠ delivery_address module not available. Skipping PASS 2.")
        logger.warning("  Delivery Address will remain NULL.")
    else:
        try:
            os.makedirs(CROPS_FOLDER, exist_ok=True)
        except Exception as e:
            logger.warning("⚠ Could not create crops folder %s: %s", CROPS_FOLDER, e)

        try:
            logger.info("Calling delivery-address extractor...")
            logger.info("  Input PDF: %s", pdf_path)
            logger.info("  Target DPI: 600")
            da_result = None

            if _extract_delivery_struct:
                try:
                    da_result = _extract_delivery_struct(
                        pdf_path,
                        prefer_dpi=600,
                        poppler_path=poppler,
                        verbose=False,
                        save_crops=True,
                        crops_folder=CROPS_FOLDER
                    )
                except TypeError:
                    logger.debug("extract_delivery_address_struct() doesn't accept save_crops/crops_folder; retrying without those args.")
                    da_result = _extract_delivery_struct(
                        pdf_path,
                        prefer_dpi=600,
                        poppler_path=poppler,
                        verbose=False
                    )

                if isinstance(da_result, dict):
                    rb = da_result.get("right_box")
                    cleaned_rb = rb
                    try:
                        if isinstance(rb, str):
                            cleaned_rb = rb.strip()
                            cleaned_rb = re.sub(r'\s{2,}', ' ', cleaned_rb)
                            cleaned_rb = re.sub(r'\s*\([^)]*,', '', cleaned_rb).strip()
                    except Exception:
                        pass
                    raw_data["Delivery Address"] = cleaned_rb
                    logger.info("✓ Delivery Address extracted successfully")
                    if cleaned_rb:
                        logger.info("  Result: %s", cleaned_rb[:200] + ("..." if len(cleaned_rb) > 200 else ""))

                    crop_path = da_result.get("crop_path") or (da_result.get("crop_paths")[0] if da_result.get("crop_paths") else None)
                    if crop_path:
                        try:
                            crop_path = os.path.normpath(crop_path)
                        except Exception:
                            pass
                        logger.info("Saved debug crop to %s", crop_path)
                        raw_data["_debug_crop_path"] = crop_path
                else:
                    logger.debug("extract_delivery_address_struct returned non-dict result; falling back to v2.")
                    if _extract_delivery_v2:
                        da_v2 = _extract_delivery_v2(pdf_path, prefer_dpi=600, poppler_path=poppler)
                        if da_v2:
                            if isinstance(da_v2, dict):
                                rb = da_v2.get("right_box") or da_v2.get("right_box_raw") or da_v2.get("right_box_text")
                                cleaned = rb
                                if isinstance(rb, str):
                                    cleaned = re.sub(r'\s{2,}', ' ', rb).strip()
                                raw_data["Delivery Address"] = cleaned
                                logger.info("✓ Delivery Address (v2 dict) extracted successfully")
                                if cleaned:
                                    logger.info("  Result: %s", cleaned[:200] + ("..." if len(cleaned) > 200 else ""))
                                crop_path = da_v2.get("crop_path") or (da_v2.get("crop_paths")[0] if da_v2.get("crop_paths") else None)
                                if crop_path:
                                    try:
                                        crop_path = os.path.normpath(crop_path)
                                    except Exception:
                                        pass
                                    logger.info("Saved debug crop to %s", crop_path)
                                    raw_data["_debug_crop_path"] = crop_path
                            else:
                                cleaned = re.sub(r'\s{2,}', ' ', str(da_v2)).strip()
                                raw_data["Delivery Address"] = cleaned
                                logger.info("✓ Delivery Address (v2) extracted successfully")
                                if cleaned:
                                    logger.info("  Result: %s", cleaned[:200] + ("..." if len(cleaned) > 200 else ""))
            else:
                if _extract_delivery_v2:
                    try:
                        da_v2 = _extract_delivery_v2(pdf_path, prefer_dpi=600, poppler_path=poppler, save_crops=True, crops_folder=CROPS_FOLDER)
                    except TypeError:
                        da_v2 = _extract_delivery_v2(pdf_path, prefer_dpi=600, poppler_path=poppler)
                    if isinstance(da_v2, dict):
                        rb = da_v2.get("right_box") or da_v2.get("right_box_raw")
                        cleaned_rb = rb
                        if isinstance(rb, str):
                            cleaned_rb = re.sub(r'\s{2,}', ' ', rb).strip()
                        raw_data["Delivery Address"] = cleaned_rb
                        crop_path = da_v2.get("crop_path") or (da_v2.get("crop_paths")[0] if da_v2.get("crop_paths") else None)
                        if crop_path:
                            try:
                                crop_path = os.path.normpath(crop_path)
                            except Exception:
                                pass
                            logger.info("Saved debug crop to %s", crop_path)
                            raw_data["_debug_crop_path"] = crop_path
                    else:
                        if isinstance(da_v2, str):
                            cleaned = re.sub(r'\s{2,}', ' ', da_v2).strip()
                            raw_data["Delivery Address"] = cleaned
                            logger.info("✓ Delivery Address extracted successfully (v2)")
                            logger.info("  Result: %s", cleaned[:200] + ("..." if len(cleaned) > 200 else ""))
                        else:
                            logger.warning("Delivery address extraction returned unexpected type.")
        except Exception as e:
            logger.error("✗ Delivery Address extraction failed: %s", e, exc_info=True)
            logger.warning("  Delivery Address will remain NULL in output")

    # ============================================
    # SAVE RAW DATA (Optional)
    # ============================================
    if save_raw_path:
        try:
            os.makedirs(os.path.dirname(save_raw_path), exist_ok=True)
            with open(save_raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            logger.info("\n✓ RAW JSON saved: %s", save_raw_path)
        except Exception as e:
            logger.warning("⚠ Failed to save RAW JSON %s: %s", save_raw_path, e)

    # ============================================
    # DATA TRANSFORMATION (Check database mappings)
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("DATA TRANSFORMATION: Checking database mappings...")
    logger.info("=" * 60)
    
    try:
        from .data_transformation import transform_extracted_data
        
        transformation_result = transform_extracted_data(raw_data)
        
        if transformation_result["transformed"]:
            logger.info("✓ Data transformation completed:")
            for change in transformation_result["changes"]:
                logger.info(f"  • {change['field']}: '{change['from']}' → '{change['to']}'")
            # Update raw_data with transformed values
            raw_data = transformation_result["data"]
        else:
            logger.info("✓ No data transformations needed")
    
    except ImportError as e:
        logger.warning("⚠ Data transformation module not available: %s", e)
        logger.warning("  Skipping data transformation step")
    except Exception as e:
        logger.error("✗ Data transformation failed: %s", e, exc_info=True)
        logger.warning("  Returning original extracted data without transformation")
    
    # ============================================
    # RETURN COMPLETE RAW DATA
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info("Fields extracted: %d/%d", 
                sum(1 for v in raw_data.values() if v is not None), 
                len(raw_data))
    
    return raw_data


# -------------------------
# CLI Interface (for testing)
# -------------------------
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Client 1 Format 1 Extractor (Two-Pass: Tesseract + PaddleOCR)"
    )
    parser.add_argument("pdf_path", help="Path to input PDF file")
    parser.add_argument("--tesseract", dest="tesseract_cmd", help="Path to Tesseract executable")
    parser.add_argument("--poppler", dest="poppler_path", help="Path to Poppler bin folder (Windows)")
    parser.add_argument("--save-json", dest="save_raw_path", help="Path to save raw JSON output")
    
    args = parser.parse_args()
    
    try:
        result = run(
            args.pdf_path,
            tesseract_cmd=args.tesseract_cmd,
            poppler_path=args.poppler_path,
            save_raw_path=args.save_raw_path
        )
        
        print("\n" + "=" * 60)
        print("FINAL OUTPUT (RAW DATA)")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error("FATAL ERROR: %s", e, exc_info=True)
        sys.exit(1)
