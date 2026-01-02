# engine/extractors/client1_format1.py
# -------------------------------------------------------------
# Client 1 - Format 1 OCR Extractor (Two-Pass Architecture)
# PASS 1: Tesseract @ DPI 300 for ALL fields EXCEPT Delivery Address
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
import cv2  # Added for deskewing
import numpy as np # Added for matrix operations
from difflib import SequenceMatcher # Added for fuzzy matching

# Disable PIL decompression bomb limit to allow large camera-captured images
Image.MAX_IMAGE_PIXELS = None

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

# Optional AI-assisted refinement for specific fields
_HAS_AI_REFINER = False
_refine_consignee = None
try:
    from engine.extractors.ai_refine_all_fields import refine_consignee
    _HAS_AI_REFINER = True
    _refine_consignee = refine_consignee
except Exception:
    _HAS_AI_REFINER = False
    _refine_consignee = None

# Optional salvage helper for low-alpha / code-heavy lines
_salvage_consignee = None
try:
    from engine.extractors.consignee import salvage_consignee
    _salvage_consignee = salvage_consignee
except Exception:
    _salvage_consignee = None

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
# Tesseract / Poppler detection helpers
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
    """Create preprocessed image variants for better OCR - enhanced for tilted text AND spaced initials"""
    img = _rotate_upright(img)
    
    # Upscale image for better character recognition (especially for spaced letters)
    # Increase resolution by 1.5x to help Tesseract detect spaces between letters
    width, height = img.size
    img = img.resize((int(width * 1.5), int(height * 1.5)), Image.Resampling.LANCZOS)
    
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
        # Use larger block size to preserve character spacing
        thresh = cv2.adaptiveThreshold(cv_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2)
        
        # IMPORTANT: Use minimal morphological operations to preserve spacing
        # Smaller kernel to avoid merging spaced characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL
        enhanced = Image.fromarray(morph)
    except ImportError:
        # If OpenCV not available, use PIL operations
        enhanced = ImageOps.autocontrast(enhanced)
        enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))  # Noise reduction
    
    return [g, sharp, enhanced]


def _ocr_configs_fast(img: Image.Image) -> List[str]:
    """Run multiple Tesseract configs and return text results - enhanced for tilted text AND spaced initials"""
    cfgs = [
        # Standard configs with interword space preservation
        r"--oem 1 --psm 6 -c preserve_interword_spaces=1",
        r"--oem 1 --psm 4 -c preserve_interword_spaces=1",
        r"--oem 1 --psm 3 -c preserve_interword_spaces=1",
        # PSM 13: Raw line - treats image as single text line, good for spaced characters
        r"--oem 1 --psm 13 -c preserve_interword_spaces=1",
        # PSM 8: Single word - can help with spaced initials
        r"--oem 1 --psm 8 -c preserve_interword_spaces=1",
        # PSM 7: Single text line - another option for spaced characters
        r"--oem 1 --psm 7 -c preserve_interword_spaces=1",
        # PSM 1: Automatic with OSD - fallback
        r"--oem 1 --psm 1 -c preserve_interword_spaces=1",
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
# Delivery Address Helpers (Ported from Format 3 for Robustness)
# -------------------------

def clean_trailing_noise(text):
    """Strip noise and unwanted artifacts from the end of the extracted name."""
    if not text:
        return text
    text = text.strip()
    
    # 1. Strip non-alphanumeric trailing characters (symbols)
    text = re.sub(r'[^a-zA-Z0-9)\]]+$', '', text).strip()
    
    # 2. Handle cases like "COMPANY LIMITED x"
    if len(text) > 3:
        text = re.sub(r'\s+[a-z0-9]$', '', text).strip()
        text = re.sub(r'\s+[xX]$', '', text).strip()
        
    return text.strip()

def get_header_points(image_cv):
    """Find multiple points along the 'Name & Address of Delivery' header to detect curvature."""
    # Use PSM 6 to detect lines/words
    data = pytesseract.image_to_data(image_cv, config='--psm 6', output_type=pytesseract.Output.DICT)
    points = []
    
    for i in range(len(data['text'])):
        text = data['text'][i].lower().strip()
        if not text: continue
            
        # Match "Name", "Address", "Delivery"
        if any(k in text for k in ['name', 'addr', 'deliv']):
            if data['conf'][i] > 25:
                points.append({
                    'x': data['left'][i] + data['width'][i] // 2,
                    'y': data['top'][i] + data['height'][i] // 2,
                    'left': data['left'][i],
                    'right': data['left'][i] + data['width'][i],
                    'conf': data['conf'][i]
                })
    
    if not points:
        return None
        
    # Standardize to one line (filter outliers in Y)
    if points:
        avg_y = np.median([p['y'] for p in points])
        line_points = [p for p in points if abs(p['y'] - avg_y) < 25]
    else:
        line_points = []
    
    if not line_points:
        return None
        
    return sorted(line_points, key=lambda p: p['x'])

def piecewise_deskew(image, points, target_y=20, crop_height=125):
    """Straighten the image based on a set of control points along a curve."""
    if not points:
        return image
        
    (h, w) = image.shape[:2]
    map_x = np.zeros((crop_height, w), np.float32)
    map_y = np.zeros((crop_height, w), np.float32)

    if len(points) < 2:
        # Fallback: Just vertical shift
        local_y = points[0]['y']
        for cy in range(crop_height):
            for x in range(w):
                map_x[cy, x] = x
                map_y[cy, x] = local_y + (cy - target_y)
    else:
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        
        for x in range(w):
            if x <= xs[0]:
                local_y = ys[0]
            elif x >= xs[-1]:
                local_y = ys[-1]
            else:
                for i in range(len(xs)-1):
                    if xs[i] <= x <= xs[i+1]:
                        ratio = (x - xs[i]) / (xs[i+1] - xs[i])
                        local_y = ys[i] + ratio * (ys[i+1] - ys[i])
                        break
            
            for cy in range(crop_height):
                map_x[cy, x] = x
                map_y[cy, x] = local_y + (cy - target_y)
            
    return cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def is_stop_line(text):
    """Check if a line marks the end of the address block."""
    text_upper = text.upper().strip()
    
    # Specific stop markers for Format 1
    stop_starts = ["PHONE", "STATE", "MOB", "EMAIL", "PH:", "PH :"]
    for s in stop_starts:
        if text_upper.startswith(s):
            return True
            
    # Check for K001 pattern if it appears at the bottom (unlikely but safe)
    if re.match(r'^K\d{3}', text_upper):
        return False # This is actually part of the address code, usually at the start/left
        
    # Check for State Code: 33 pattern
    if "STATE CODE" in text_upper:
        return True
        
    return False

def clean_address_lines_robust(lines):
    """Clean up the extracted address text, respecting stop markers."""
    final_lines = []
    
    for line in lines:
        l = line.strip()
        if not l:
            continue
            
        # Check for stop marker
        if is_stop_line(l):
            # If we hit "Phone No" or "State Code", stop collecting
            break
            
        # Clean line
        # Strip specific trailing noise chars like ; | !
        l = re.sub(r'\s*[;|!\\/]+$', '', l).strip()
        
        # Strip trailing "K001" if it was erroneously appended to a line (usually it's on the left)
        # But if the user WANTS K001, we should keep it. 
        # The user said "take k001 also".
        
        if l:
            final_lines.append(l)
            
    # Join with space (comma separation can be added if needed, but space is safer for now)
    return ", ".join(final_lines)

def extract_delivery_address_robust(page_image, page_num=0, debug=False) -> str:
    """
    Extract Delivery Address using Bend-Crop (piecewise deskewing).
    Designed to capture 'K001' on the left and stop at 'Phone No' on the bottom.
    Dynamically adjusts crop height to exclude bottom text visually.
    """
    try:
        # Convert to OpenCV format
        img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]
        
        # Search area: generous
        search_y1, search_y2 = int(height * 0.10), int(height * 0.60)
        search_x1, search_x2 = int(width * 0.40), int(width * 0.98)
        search_area = img_cv[search_y1:search_y2, search_x1:search_x2]
        
        header_points = get_header_points(search_area)
        
        if header_points:
            hw = header_points[-1]['right'] - header_points[0]['left']
            hx_start = header_points[0]['left']
            
            # Deskew deep enough to catch everything initially
            straightened = piecewise_deskew(search_area, header_points, target_y=20, crop_height=600)
            
            # --- Vertical Line Detection (for strict left crop) ---
            # Create a binary image to detect vertical lines
            gray_straight = cv2.cvtColor(straightened, cv2.COLOR_BGR2GRAY)
            bw = cv2.adaptiveThreshold(~gray_straight, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
            
            # Use vertical structure element
            vertical = bw.copy()
            # Length of line to detect: fairly long so we don't pick up text stems
            v_len = straightened.shape[0] // 15
            verticalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
            vertical = cv2.erode(vertical, verticalStructure)
            vertical = cv2.dilate(vertical, verticalStructure)
            
            # Find contours of vertical lines
            cnts, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the best vertical line to the LEFT of the header
            # And also to the RIGHT of the header (to avoid cutting long addresses)
            
            hx_start = header_points[0]['left']
            hx_end = header_points[-1]['right']
            
            best_x_left = -1
            min_dist_left = float('inf')
            
            best_x_right = -1
            min_dist_right = float('inf')
            
            # Debug detected lines
            if debug:
                line_debug_img = straightened.copy()
            
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                cx = x + w // 2
                
                if debug:
                    cv2.rectangle(line_debug_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
                
                # Check if it's a valid separator (must be TALL to be a column separator)
                # 50px is too short (can be text/noise). Use 150px to find the main column line.
                if h < 150: continue 
                
                # --- LEFT SIDE SNAP ---
                if cx < hx_start:
                    dist = hx_start - cx
                    # We want the NEAREST line to the left (the immediate column separator)
                    # "Leftmost" would pick the start of the previous column (e.g. PO No), which is wrong.
                    if dist < min_dist_left and dist < (hw * 0.45):
                        min_dist_left = dist
                        best_x_left = x + w # Snap to right side of the line rect (cleaner than cx+w)
                        
                # --- RIGHT SIDE SNAP ---
                elif cx > hx_end:
                    # We want the RIGHTMOST line (table border) to avoid snapping to 
                    # noise streaks inside the address text.
                    if cx > best_x_right:
                        best_x_right = cx # Snap to left side of the line

            if debug:
                debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_debug_f1"
                if not os.path.exists(debug_dir): os.makedirs(debug_dir)
                cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_lines_debug.png"), line_debug_img)
            
            # --- Determine Crop Coordinates ---
            crop_y1 = 45 # Start just below header
            crop_y2_initial = 580 # Deep probe
            
            # Left Crop
            if best_x_left != -1:
                logger.info(f"[Delivery] Snapping left crop to vertical line at x={best_x_left}")
                crop_x1 = best_x_left + 2 
            else:
                logger.info("[Delivery] No left vertical separator found. Using fallback offset.")
                crop_x1 = max(0, hx_start - int(hw * 0.20)) 
                
            # Right Crop - KEY FIX for "POONAMALLE HIGH ROAD"
            if best_x_right != -1:
                logger.info(f"[Delivery] Snapping right crop to vertical line at x={best_x_right}")
                crop_x2 = best_x_right - 2
            else:
                # Fallback: USE FULL WIDTH instead of arbitrary cut
                # The search area (0.98 width) is already bounded safely enough for typical cases
                logger.info("[Delivery] No right vertical separator found. Using full available width.")
                crop_x2 = straightened.shape[1]
            
            probe_crop = straightened[crop_y1:crop_y2_initial, crop_x1:crop_x2]
            
            if probe_crop.size == 0:
                logger.warning("[Delivery] Probe crop is empty")
                return ""
                
            # Gray & Threshold for OCR logic
            gray = cv2.cvtColor(probe_crop, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Use image_to_data to find visual boundaries of text lines
            data = pytesseract.image_to_data(thresh, config='--psm 6', output_type=pytesseract.Output.DICT)
            
            # Find the split point (Y-coord) where "Phone" or "State" appears
            # Scan words directly for stop markers (more robust than line grouping)
            cut_y = probe_crop.shape[0] 
            stop_found = False
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                word = data['text'][i].strip().lower()
                if not word: 
                    continue
                    
                # Remove common punctuation
                clean_word = re.sub(r'[^\w]', '', word)
                
                # Check for stop keywords
                # DEBUG: Log words to see what's happening
                if debug:
                    logger.info(f"    [Word Scan] '{word}' -> '{clean_word}' ({data['text'][i]}) (Y={data['top'][i]})")
                
                if clean_word in ['phone', 'state', 'mob', 'email', 'ph', 'mobile']:
                    t = int(data['top'][i])
                    # We want the highest (smallest Y) occurrence
                    if t < cut_y:
                        cut_y = t
                        stop_found = True
                        logger.info(f"  [Delivery] VISUAL STOP MATCH: '{word}' at Y={t}")

            # Apply a small margin (cut slightly above the stop word)
            if stop_found:
                cut_y = max(0, cut_y - 5)
            
            logger.info(f"  [Delivery] FINAL CUT Y: {cut_y} (Original H: {probe_crop.shape[0]})")
                
            # Create final clean crop
            final_crop = probe_crop[0:cut_y, :]
            
            # Save debug crop if requested
            if True: 
                debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_debug_f1"
                if not os.path.exists(debug_dir): os.makedirs(debug_dir)
                crop_path = os.path.join(debug_dir, f"page_{page_num}_delivery_robust.png")
                cv2.imwrite(crop_path, final_crop)
                logger.info(f"[Delivery] Saved debug crop to {crop_path}")
                
            # OCR the final crop
            final_gray = cv2.cvtColor(final_crop, cv2.COLOR_BGR2GRAY)
            _, final_thresh = cv2.threshold(final_gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(final_thresh, config='--psm 6').strip()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            if lines:
                # We can skip the 'is_stop_line' check in cleaning if the visual crop worked, 
                # but valid to keep it as a backup
                cleaned = clean_address_lines_robust(lines)
                logger.info(f"[Delivery] Extracted Robust: {cleaned}")
                return cleaned

                
    except Exception as e:
        logger.error(f"[Delivery] Robust extraction failed: {e}", exc_info=True)
        
    return ""


# -------------------------
# Date Normalization & Parsing
# -------------------------
def normalize_for_dates(s: str) -> str:
    """Normalize OCR artifacts in date strings"""
    # Single-character mappings only
    trans = str.maketrans({
        'O': '0', 'o': '0', 'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5', 'B': '8'
    })
    s = s.translate(trans)
    
    # Multi-character Unicode replacements (manual)
    s = s.replace('—', '-')  # em dash
    s = s.replace('–', '-')  # en dash
    s = s.replace('‚', ',')  # low quotation mark
    
    return s


def try_parse_date(s: str):
    """Try parsing date string with multiple formats - ENHANCED for smudged OCR"""
    if not s:
        return None
    
    # Normalize OCR errors in date string (Oâ†’0, Iâ†’1, etc.)
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
    """Extract invoice date - ENHANCED for smudged OCR (e.g., O5.1O.2O25 â†’ 05.10.2025)"""
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
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the full text being searched for debugging
    logger.info(f"[LR EXTRACTION] Full OCR text length: {len(text)} chars")
    logger.info(f"[LR EXTRACTION] Searching in text: {text[:500]}")
    
    # Look for the pattern in entire text - sometimes OCR splits L.R. label and number across lines
    # Search for "L.R" or "RR" followed by anything, then capture standalone 4-7 digit numbers
    lr_section = re.search(r'L\.?R\.?.*?(?:No|RR).*', text, re.IGNORECASE | re.DOTALL)
    if lr_section:
        logger.info(f"[LR EXTRACTION] Found L.R./RR section: {lr_section.group(0)[:200]}")
    
    # Patterns allowing OCR errors in numbers (O, I, l, S) and typos in keywords
    patterns = [
        # PRIORITY 1: Exact format from invoice header "L.R.No/RR No.: 6662"
        (r'L\.R\.No/RR\s*No\.?\s*:\s*([0-9OIlSs]{2,7})', re.IGNORECASE),
        # PRIORITY 2: Similar variations with colon
        (r'L\.?R\.?\s*No\.?/RR\s*No\.?\s*:\s*([0-9OIlSs]{2,7})', re.IGNORECASE),
        # Standard formats with No/No. - prioritize these (avoid "Date" to not match dates)
        (r'L\.?R\.?\s*No\.?\s*/?\s*RR\s*No?\.?[:.\s/\\-]*([0-9OIlSs]{2,7})(?:\s|$|[A-Z])', re.IGNORECASE),
        (r'L\.?R\.?\s*No\.?\s*/\s*RR\s*No?\.?[:.\s]*([0-9OIlSs]{2,7})(?:\s|$|[A-Z])', re.IGNORECASE),
        # Compact format (most common) - No or No. only (not Date)
        (r'L\.?R\.?No\.?/RR\s*No?\.?[:.\s]*([0-9OIlSs]{2,7})(?:\s|$|[A-Z])', re.IGNORECASE),
        # With typos (Na instead of No)
        (r'L\.?R\.?.*RR\s*N[oa]\.?[:.\s/\\-]*([0-9OIlSs]{2,7})(?:\s|$|[A-Z])', re.IGNORECASE),
        (r'RR\s*N[oa]\.?[:.\s/\\-]*([0-9OIlSs]{2,7})(?:\s|$|[A-Z])', re.IGNORECASE),
        # Look for numbers near L.R. keyword (may be split across lines)
        (r'L\.?R\.?.*?No.*?[:.\s]+([0-9OIlSs]{4,7})(?:\s|$)', re.IGNORECASE | re.DOTALL),
        # Simple RR/LR with colon or space
        (r'\bRR\s*[:.\s]+([0-9OIlSs]{4,7})(?:\s|$|[A-Z])', re.IGNORECASE),
        (r'\bLR\s*[:.\s]+([0-9OIlSs]{4,7})(?:\s|$|[A-Z])', re.IGNORECASE),
    ]
    
    found_matches = []
    for i, (pattern, flags) in enumerate(patterns):
        matches = re.finditer(pattern, text, flags)
        for m in matches:
            extracted = m.group(1)
            logger.info(f"[LR EXTRACTION] Pattern {i+1} matched: '{m.group(0)[:50]}' -> extracted: '{extracted}'")
            
            # Normalize OCR errors and clean
            normalized = _normalize_ocr_smudge(extracted)
            cleaned = re.sub(r'[^0-9]', '', normalized)
            
            # Validate: should be 2-7 digits
            if 2 <= len(cleaned) <= 7:
                # Skip if it looks like a date
                if len(cleaned) == 8 and cleaned[0] in '0123':
                    logger.info(f"[LR EXTRACTION] Skipping 8-digit date: {cleaned}")
                    continue
                if len(cleaned) == 6 and cleaned[0] in '0123' and cleaned[2] in '01':
                    logger.info(f"[LR EXTRACTION] Skipping 6-digit date: {cleaned}")
                    continue
                # Skip 4-digit years (2020-2099, 1900-1999)
                if len(cleaned) == 4 and cleaned[:2] in ['19', '20']:
                    logger.info(f"[LR EXTRACTION] Skipping 4-digit year: {cleaned}")
                    continue
                # Skip HSN codes (4 digits typically 2XXX, 6XXX, 7XXX, 8XXX, 9XXX)
                if len(cleaned) == 4 and cleaned[0] in '234567890':
                    # Check if HSN Code appears nearby in the match
                    context = text[max(0, m.start()-50):min(len(text), m.end()+50)]
                    if 'HSN' in context.upper() or 'CODE' in context.upper():
                        logger.info(f"[LR EXTRACTION] Skipping HSN code: {cleaned}")
                        continue
                
                found_matches.append((cleaned, m.start(), i+1))
    
    # Return the first valid match (patterns are in priority order)
    if found_matches:
        # Sort by pattern priority (lower pattern number = higher priority)
        found_matches.sort(key=lambda x: (x[2], x[1]))
        best_match = found_matches[0][0]
        logger.info(f"[LR EXTRACTION] Successfully extracted: {best_match}")
        return best_match
    
    logger.warning("[LR EXTRACTION] No L.R. number found in text")
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
    import logging
    logger = logging.getLogger(__name__)
    
    # Allow OCR variants of 'of' (e.g., '0f', '01') and optional separators
    header_re = re.compile(
        r'(?:Name\s*(?:&|and)\s*Address\s*(?:of|0f|o1|01|:)?\s*(?:Recipient|Consignee))\s*:?',
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
        # Accept lines with common business words
        if re.search(r'\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING|CEMENT|ENGINEERS?|AGENCIES|AGENCY|SOLUTIONS|TECH|ENTERPRISES|LOGISTICS|SYSTEMS)\b', U):
            return True
        # Accept uppercase words (company names are typically uppercase)
        if U == s.strip() and 1 <= len(U.split()) <= 6 and len(U) >= 4:
            return True
        # Must have reasonable letter content
        letters = re.findall(r'[A-Za-z]', s)
        if not letters:
            return False
        alpha_ratio = sum(ch.isalpha() for ch in letters) / len(letters)
        # Remove embedded code-like tokens and dates which corrupt alpha-ratio
        # but may be present on the same OCR line as the company name.
        # If a code token is found, it likely separates columns (Consignee | PO | Delivery).
        # We don't modify 's' here because this is just a boolean check.
        # The actual cleaning happens in _clean_company_line.


        # Reject lines with too many special characters/numbers (likely OCR garbage)
        if alpha_ratio < 0.65:
            return False
        # Reject lines with excessive underscores, brackets, or special chars (OCR artifacts)
        if re.search(r'[_\[\]\{\}]{2,}', s):
            logger.info(f"[CONSIGNEE] Rejecting garbage line: {s}")
            return False
        return True

    def _clean_company_line(raw: str) -> Optional[str]:
        s = (raw or "").strip(" :-\t")
        
        # Remove OCR garbage characters
        s = re.sub(r'[_\[\]\{\}\|]+', ' ', s)
        
        # Remove embedded code-like tokens and dates which corrupt alpha-ratio
        # but may be present on the same OCR line as the company name.
        # If a code token is found, it likely separates columns (Consignee | PO | Delivery).
        code_pat = r'\b[A-Z]{2,6}(?:/[A-Z0-9\-\./]+)+\b'
        if re.search(code_pat, s):
            # Split and pick the best part
            parts = re.split(code_pat, s)
            # Filter empty parts
            parts = [p.strip() for p in parts if p.strip()]
            if parts:
                # Score parts: prefer ones with "Pvt", "Ltd", etc. and higher alpha ratio
                def _score_part(p):
                    p_clean = re.sub(r'\d|[^A-Za-z]', '', p)
                    alpha = sum(c.isalpha() for c in p_clean)
                    denom = len(re.sub(r'\s+', '', p)) or 1
                    # Bonus for company keywords
                    bonus = 0
                    if re.search(r'\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING)\b', p, re.IGNORECASE):
                        bonus = 1.0
                    return (bonus, alpha / denom, len(p.split()))
                parts.sort(key=_score_part, reverse=True)
                s = parts[0]
        
        s = re.sub(r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', ' ', s)
        # Remove common trailing debug tokens like 'Recipient Code : 641056A019'
        s = re.sub(r'Recipient\s+Code\s*[:\-]\s*\S+', ' ', s, flags=re.IGNORECASE)
        # If pipe-separated segments exist, prefer the segment that looks most like a company name
        if '|' in s:
            parts = [p.strip() for p in s.split('|') if p.strip()]
            if parts:
                def _score_part_pipe(p):
                    p_clean = re.sub(r'\d|[^A-Za-z]', '', p)
                    alpha = sum(c.isalpha() for c in p_clean)
                    denom = len(re.sub(r'\s+', '', p)) or 1
                    return (alpha / denom, len(p.split()))
                parts.sort(key=_score_part_pipe, reverse=True)
                s = parts[0]

        
        m_stop = stop_tokens.search(s)
        if m_stop:
            s = s[:m_stop.start()].rstrip()
        m = suffix_pat.search(s)
        if m:
            s = m.group(1)
        s = re.split(r'\s+\d[\d\s/\-\.]*', s, maxsplit=1)[0]
        s = re.sub(r'\s{2,}', ' ', s).strip(' ,:-.')
        
        # Clean up punctuation: "K.S., TRADERS" -> "K.S. TRADERS"
        s = s.replace('.,', '.')
        s = s.replace(',', ' ')
        s = re.sub(r'\s+', ' ', s).strip()

        # Remove trailing separator-like characters (e.g., "AVS Tech I" -> "AVS Tech")
        # 'I' is often a misread pipe '|'
        if s.endswith(' I') or s.endswith(' l') or s.endswith(' |'):
             s = s[:-2].strip()

        # Remove trailing two-letter patterns ending with 'O' at the END only (e.g., PO, QO, WO, EO)
        # BUT never strip "CO" as it's a valid company suffix
        # This strips: "COMPANY NAME PO", "COMPANY NAME QO 123", etc.
        # This preserves: "COMPANY CO", "TRADING CO LTD", etc.
        s = re.sub(r'\s+(?!CO\b)[A-Z]O\b.*$', '', s, flags=re.IGNORECASE)

        # extra: collapse duplicated repeated phrase if present (A A)
        s = _collapse_duplicate_phrase(s)

        # Preserve original spaced single-letter sequences (e.g., "B N R")
        # Some OCR outputs single letters separated by spaces which are meaningful
        # in company names (like initials). Detect these sequences in the raw
        # input and, if they were collapsed during cleaning (e.g., "BNR"),
        # restore them to their spaced form before further validation.
        # Preserve original spaced single-letter sequences (e.g., "B N R")
        # Some OCR outputs single letters separated by spaces which are meaningful
        # in company names (like initials). Detect these sequences in the raw
        # input and, if they were collapsed during cleaning (e.g., "BNR"),
        # restore them to their spaced form before further validation.
        try:
            seqs = re.findall(r"\b(?:[A-Za-z]\s+){1,}[A-Za-z]\b", raw or "")
            for seq in seqs:
                letters = re.findall(r'[A-Za-z]', seq)
                # Only restore short spaced-letter sequences (2-3 letters). Avoid
                # restoring longer words which are likely real names (e.g., VASU).
                if 2 <= len(letters) <= 3:
                    spaced = ' '.join(letters)
                    collapsed = ''.join(letters)
                    # Replace collapsed form in current cleaned string with spaced form (case-insensitive)
                    s = re.sub(re.escape(collapsed), spaced, s, flags=re.IGNORECASE)
        except Exception:
            # If anything goes wrong here, continue without restoration
            pass

        # Split mixed 1-2 letter sequences (e.g., "T RS" -> "T R S")
        # This handles cases where OCR missed a space inside a 2-letter initial part
        try:
            # Look for patterns like "X YY" or "XX Y" or "XX YY"
            # We want to split the 2-letter parts into 1-letter parts
            # Be careful with common 2-letter words like "TO", "OF", "CO" if they are part of a sentence
            # But in a company name line, "T RS" is likely "T R S".
            
            def _split_mixed(m):
                # Split all parts in the match into single chars separated by space
                return " ".join(list(m.group(0).replace(" ", "")))

            # Pattern: Single Space Double (e.g. "T RS")
            s = re.sub(r'\b[A-Z]\s+[A-Z]{2}\b', _split_mixed, s)
            # Pattern: Double Space Single (e.g. "TR S")
            s = re.sub(r'\b[A-Z]{2}\s+[A-Z]\b', _split_mixed, s)
            # Pattern: Double Space Double (e.g. "TR SL")
            s = re.sub(r'\b[A-Z]{2}\s+[A-Z]{2}\b', _split_mixed, s)
            
        except Exception:
            pass

        # POST-OCR FIX: Split merged initials (e.g., "TRS" -> "T R S")
        # DISABLED: This is too aggressive - we can't reliably tell if original had "SLT" or "S L T"
        # OCR gives us "SLT" in both cases, so we can't distinguish them.
        # The user wants exact extraction, so we should preserve what OCR gives us.
        # 
        # If user wants to enable this for specific cases, they can uncomment and adjust.
        # try:
        #     tokens = s.split()
        #     if tokens:
        #         first = tokens[0]
        #         # List of common business suffixes that often follow initials
        #         suffixes = {"AGENCIES", "AGENCY", "TRADERS", "TRADING", "ENGINEERS", "CEMENT", "INDUSTRIES", "SERVICES", "CONTRACTORS", "CONSTRUCTIONS", "COMPANY", "ENTERPRISES", "ENTERPRISE", "LTD", "PVT", "PRIVATE", "STEELS", "STEEL", "LOGISTICS", "SYSTEMS"}
        #         # Only split very short merged initials (2-3 letters). Avoid
        #         # splitting normal short words like 'VASU' (4 letters) or valid words like 'CO'
        #         if first.isalpha() and first.isupper() and 2 <= len(first) <= 3 and first != "CO":
        #             follow = tokens[1].upper() if len(tokens) > 1 else ""
        #             # If the next token is a known business suffix, it's likely the initials were merged
        #             if follow in suffixes:
        #                 tokens[0] = ' '.join(list(first))
        #                 s = ' '.join(tokens)
        #                 logger.info(f"[CONSIGNEE] Split merged initials: '{first}' -> '{tokens[0]}'")
        # except Exception:
        #     pass
        
        # Fix common OCR errors in company names
        # FRADERS â†’ TRADERS (F is often misread T)
        s = re.sub(r'\bFRADERS\b', 'TRADERS', s, flags=re.IGNORECASE)
        # Also handle other common OCR misreads in business names
        s = re.sub(r'\bFRADING\b', 'TRADING', s, flags=re.IGNORECASE)
        s = re.sub(r'\bFRANSPORT\b', 'TRANSPORT', s, flags=re.IGNORECASE)
        
        # STRICT validation: Reject garbage from squeezed/poor quality OCR
        # Company names should be at least 3 chars and mostly alphabetic
        if len(s) < 3:
            logger.info(f"[CONSIGNEE] Rejecting - too short: '{s}'")
            return None
        
        # Count alphabetic vs total characters
        alpha_count = sum(c.isalpha() for c in s)
        total_visible = sum(not c.isspace() for c in s)
        
        if total_visible == 0:
            logger.info(f"[CONSIGNEE] Rejecting - no visible chars: '{s}'")
            return None
            
        alpha_ratio = alpha_count / total_visible if total_visible > 0 else 0
        
        # Require at least 70% alphabetic characters (allows for "&", ".", etc.)
        if alpha_ratio < 0.70:
            logger.info(f"[CONSIGNEE] Rejecting - low alpha ratio ({alpha_ratio:.2f}): '{s}'")
            return None
        
        # Reject if contains non-standard chars (OCR garbage indicators)
        # Allow commas, slashes, parentheses as they are common in company names
        if re.search(r'[^\w\s\-\.\&,\(\)\/]', s):
            logger.info(f"[CONSIGNEE] Rejecting - contains garbage chars: '{s}'")
            return None
        
        # Additional check: reject very short words that are likely OCR garbage
        words = s.split()
        if len(words) == 1 and len(words[0]) <= 2:
            logger.info(f"[CONSIGNEE] Rejecting - single short word: '{s}'")
            return None
        
        return s or None

    logger.info(f"[CONSIGNEE] Searching for recipient/consignee in {len(lines)} lines")
    
    for idx, line in enumerate(lines):
        m = header_re.search(line)
        if not m:
            continue
        
        logger.info(f"[CONSIGNEE] Found header at line {idx}: {line[:100]}")
        
        # Check inline name
        tail = (line[m.end():] or "").strip(" :-")
        if tail and _is_company_line(tail):
            result = _clean_company_line(tail)
            if result:
                logger.info(f"[CONSIGNEE] Extracted from header line: {result}")
                return result
        
        # Check next lines: gather consecutive company-like lines and join them.
        company_lines: List[str] = []
        # Lines that should stop accumulation (address/box/floor info etc.)
        stop_indicators = re.compile(r'\b(?:GSTIN|GST|STATE|PLACE\s+OF\s+SUPPLY|PO\s*NO(?:/DATE)?|DATE|EMAIL|MOBILE|PHONE|PAN|PIN|POST|P\.O\.|FLOOR|FL|NO\b|NO\.|BUILDING|HOUSE|STREET|ROAD|LANE)\b', re.IGNORECASE)

        for j in range(idx + 1, min(idx + 10, len(lines))):
            cand = (lines[j] or "").strip()
            if not cand:
                # blank line - may separate blocks; stop if we've already collected something
                if company_lines:
                    break
                continue
            logger.info(f"[CONSIGNEE] Checking line {j}: {cand[:100]}")

            # Explicitly stop if line starts with "po" (e.g. "po 30/...")
            # This prevents merging PO details into the company name
            if re.match(r'^po\b', cand, re.IGNORECASE):
                logger.info(f"[CONSIGNEE] Stopping at PO line: {cand}")
                break

            # If this line contains a clear stop indicator, decide whether to accept or stop.
            # In some PDFs the company name and tokens like 'EMAIL' or 'GSTIN' may appear
            # on the same OCR line (noise). If the line also looks company-like, accept
            # it but allow the cleaner to strip trailing stop-token fragments.
            si = stop_indicators.search(cand)
            if si:
                # Accept this line if it has clear alphabetic/company content even
                # though it contains stop-indicator tokens (e.g. 'EMAIL') that
                # appear on the same OCR line. This handles cases like
                # 'Larsen and Toubro Limiited  EMAIL CONFIRMATION'.
                if _is_company_line(cand) or re.search(r'\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING|AGENCIES|AGENCY|ENGINEERS|SOLUTIONS|TECH|ENTERPRISES|LOGISTICS|SYSTEMS)\b', cand, re.IGNORECASE) or (
                    len(re.findall(r'[A-Za-z]', cand)) >= 6 and len(cand.split()) >= 2
                ):

                    logger.info(f"[CONSIGNEE] Line {j} contains stop-indicator but looks company-like, accepting: {cand}")
                    company_lines.append(cand)
                    if len(company_lines) >= 3:
                        break
                    continue
                else:
                    logger.info(f"[CONSIGNEE] Stopping accumulation at line {j} due to indicator: {cand}")
                    break

            # If the line is mostly numeric or contains 'FLOOR'/'NO', treat as address and stop
            if re.search(r'\b(FLOOR|FL|NO\.?|\d{2,})\b', cand, re.IGNORECASE) and not re.search(r'[A-Za-z]{3,}', cand):
                logger.info(f"[CONSIGNEE] Detected address-like/numeric line at {j}: {cand}")
                break

            # Accept this line as part of the company name if it looks like a company line
            if _is_company_line(cand) or re.search(r'[A-Za-z]', cand):
                company_lines.append(cand)
                # continue collecting up to 3 lines to form a fuller company name
                if len(company_lines) >= 3:
                    break
                continue
            # If not company-like, stop accumulation
            logger.info(f"[CONSIGNEE] Line {j} rejected as non-company: {cand}")
            break
        # After accumulation attempt, try the longest candidate first, then shorter ones
        if company_lines:
            for take in range(len(company_lines), 0, -1):
                candidate = ' '.join(company_lines[:take])
                result = _clean_company_line(candidate)
                if result:
                    logger.info(f"[CONSIGNEE] Extracted (combined lines): {result}")
                    return result
        break

    logger.warning("[CONSIGNEE] No valid consignee found in header/nearby lines")

    # Centralized line-based fallback: look for header lines and then scan the next
    # few lines for company-like content (more robust than a single regex capture).
    try:
        for idx, line in enumerate(lines):
            if header_re.search(line):
                candidate_lines = []
                # scan the next few lines for plausible company lines
                for j in range(idx + 1, min(idx + 8, len(lines))):
                    ln = (lines[j] or "").strip()
                    if not ln:
                        if candidate_lines:
                            break
                        continue
                    # Skip lines that are mostly labels or headers
                    if re.search(r'\b(PO\s*NO|PO\s*DATE|NAME\s*&\s*ADDRESS|RECIPIENT|ADDRESS|EMAIL\s*CONFIRMATION)\b', ln, re.IGNORECASE):
                        continue
                    # require at least some alphabetic content
                    if len(re.findall(r'[A-Za-z]', ln)) < 3:
                        continue
                    candidate_lines.append(ln)
                    # try combined candidates longest-first as we grow
                    for take in range(len(candidate_lines), 0, -1):
                        cand_join = ' '.join(candidate_lines[:take])
                        # Heuristic: prefer multi-word/company-keyword candidates.
                        # Make the preference pattern configurable via the
                        # `PREFERRED_NAME_TOKENS` env var (comma-separated list).
                        # Default: generic company keywords only (no specific brand names).
                        pref_tokens = os.getenv("PREFERRED_NAME_TOKENS")
                        if pref_tokens:
                            tokens = [t.strip() for t in pref_tokens.split(",") if t.strip()]
                            # build a safe regex from user-specified tokens
                            pattern = r"\b(" + "|".join([re.escape(t) for t in tokens]) + r")\b"
                        else:
                            pattern = r"\b(LIMITED|LTD|PVT|PVT\.? LTD|CONSTRUCTION|CONSTRUCTIONS|AGENCIES|TRADERS|ENGINEERS|CORPORATION|CORP)\b"
                        prefers = re.search(pattern, cand_join, re.IGNORECASE)
                        if not prefers and len(cand_join.split()) < 2:
                            # skip single-token acronyms like 'SGST' as candidates
                            continue
                        cand_clean = _clean_company_line(cand_join)
                        if cand_clean:
                            logger.info(f"[CONSIGNEE] Line-fallback extracted: {cand_clean}")
                            return cand_clean
                # no company found for this header, continue searching other headers
    except Exception:
        logger.debug("[CONSIGNEE] Line-based fallback failed", exc_info=True)

    # Fallback: look for any line containing 'RECIPIENT' or 'CONSIGNEE' (OCR may have mangled header)
    for idx, line in enumerate(lines):
        if re.search(r'\b(RECI?P?I?ENT|CONSIGNEE)\b', line, re.IGNORECASE):
            logger.info(f"[CONSIGNEE] Fallback header found at line {idx}: {line[:100]}")
            # reuse accumulation logic: collect following company-like lines
            company_lines = []
            stop_indicators = re.compile(r'\b(?:GSTIN|GST|STATE|PLACE\s+OF\s+SUPPLY|PO\s*NO(?:/DATE)?|DATE|EMAIL|MOBILE|PHONE|PAN|PIN|POST|P\.O\.|FLOOR|FL|NO\b|NO\.|BUILDING|HOUSE|STREET|ROAD|LANE)\b', re.IGNORECASE)
            for j in range(idx + 1, min(idx + 10, len(lines))):
                cand = (lines[j] or "").strip()
                if not cand:
                    if company_lines:
                        break
                    continue
                # similar permissive handling as above
                si = stop_indicators.search(cand)
                if si:
                    if _is_company_line(cand) or re.search(r'\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING|AGENCIES|AGENCY|ENGINEERS)\b', cand, re.IGNORECASE):
                        company_lines.append(cand)
                        if len(company_lines) >= 3:
                            break
                        continue
                    break
                if re.search(r'\b(FLOOR|FL|NO\.?|\d{2,})\b', cand, re.IGNORECASE) and not re.search(r'[A-Za-z]{3,}', cand):
                    break
                if _is_company_line(cand) or re.search(r'[A-Za-z]', cand):
                        company_lines.append(cand)
                        if len(company_lines) >= 3:
                            break
                        continue
                else:
                    break
            if company_lines:
                for take in range(len(company_lines), 0, -1):
                    candidate = ' '.join(company_lines[:take])
                    result = _clean_company_line(candidate)
                    if result:
                        logger.info(f"[CONSIGNEE] Extracted (fallback combined): {result}")
                        return result
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
    # Allow hyphen and slash as meaningful separators (e.g., chennai-south, coimbatore/ north)
    s = re.sub(r'[^A-Za-z0-9\s\-/]', ' ', s)

    # 7) Collapse whitespace and trim
    s = re.sub(r'\s+', ' ', s).strip()

    # Normalize spacing around hyphens and slashes: keep them without surrounding spaces
    s = re.sub(r'\s*-\s*', '-', s)
    s = re.sub(r'\s*/\s*', '/', s)

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

    # Reject suffix-only values like 'Pvt Ltd' which are not valid company names
    words = [w.strip(".,()[]") for w in re.split(r'\s+|[,|\\|/]', s) if w.strip()]
    if not words:
        return None
    core = [re.sub(r'[^A-Za-z]', '', w).lower() for w in words]
    suffixes = {"pvt", "ltd", "private", "limited", "llp", "co", "company", "inc", "corp", "gmbh"}
    # If result is only suffix tokens or 1-2 short tokens, reject
    if all((not c) or (c in suffixes) or (len(c) <= 2) for c in core):
        logger.info(f"[CONSIGNEE] Rejecting suffix-only/low-info consignee: '{s}'")
        return None

    # Ensure reasonable alphabetic density
    letters = re.findall(r'[A-Za-z]', s)
    total = len(re.sub(r'\s+', '', s)) or 1
    alpha_ratio = sum(ch.isalpha() for ch in s) / total
    if len(letters) < 3 or alpha_ratio < 0.5:
        logger.info(f"[CONSIGNEE] Rejecting low-information consignee (alpha_ratio={alpha_ratio:.2f}): '{s}'")
        return None

    return s if s else None


def _collapse_duplicate_phrase(s: str) -> str:
    """
    Heuristic to collapse cases where a name/phrase is duplicated back-to-back.
    Example:
      "Larsen and Toubro Limiited Larsen and Toubro Limiited (Avy" -> "Larsen and Toubro Limiited"
      "KARTYA CONSTRUCTIONS PRIVATE L / KARTYA CONSTRUCTIONS PRIVATE L" -> "KARTYA CONSTRUCTIONS PRIVATE L"
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
    # Handle various separators: spaces, slashes, pipes, etc.
    s_norm = re.sub(r'\s+', ' ', s).strip()
    # look for exact substring repeated twice with separator (space, /, |, etc.)
    # Pattern: (8-200 chars) + (space/slash/pipe) + same chars again
    m = re.search(r'(.{8,200}?)\s*[/|\s]+\s*\1\b', s_norm, re.IGNORECASE)
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
    ("SRC", [
        re.compile(rf'S{SEP}R{SEP}C\b', re.IGNORECASE),
        re.compile(r'\bSRC\b', re.IGNORECASE)
    ]),
]


def _merge_split_letters_in_text(t: str) -> str:
    """Merge space-separated letters (O P C â†’ OPC)"""
    t = re.sub(r'(?i)\b([A-Z])\s+([A-Z])\s+([A-Z])\b', r'\1\2\3', t)
    t = re.sub(r'(?i)\b([A-Z])\s+([A-Z])\b', r'\1\2', t)
    return t


def extract_material_code_global(txt: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract cement material code (OPC53, PPC53, etc.)"""
    import logging
    logger = logging.getLogger(__name__)
    
    U = txt.upper().replace('0', 'O').replace('1', 'I').replace('5', 'S')
    U = _merge_split_letters_in_text(U)
    
    logger.info(f"[MATERIAL] Searching for material code in text (length: {len(txt)})")
    
    best = None
    for code, patterns in CODE_PATTERNS:
        for pat in patterns:
            m = pat.search(U)
            if m:
                idx = m.start()
                logger.info(f"[MATERIAL] Found '{code}' at position {idx}: '{m.group(0)}'")
                if (best is None) or (idx < best[0]):
                    best = (idx, code)
                break
    
    if best:
        logger.info(f"[MATERIAL] Best match: '{best[1]}' (method: global_regex)")
        return best[1], "global_regex"
    
    # Fallback: squash and search
    squashed = re.sub(r'[^A-Z0-9]+', '', U)
    logger.info(f"[MATERIAL] Checking squashed text: {squashed[:200]}")
    for code in ["OPC53", "PPC53", "OPC43", "PPC43", "OPC", "PPC", "PSC", "SRC"]:
        if code in squashed:
            # Convert PSC to PPC
            final_code = "PPC" if code == "PSC" else code
            logger.info(f"[MATERIAL] Found '{code}' in squashed text (method: global_squash)")
            if code == "PSC":
                logger.info(f"[MATERIAL] Converting PSC â†’ PPC")
            return final_code, "global_squash"
    
    logger.warning("[MATERIAL] No material code found")
    return None, None


def extract_quantity_weight(images: List[Image.Image], text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract quantity/weight - ENHANCED for smudged OCR (e.g., I23.456 MT â†’ 123.456 MT)"""
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
    """Extract rate per unit - ENHANCED for smudged OCR (e.g., Rs. 6500/MT, Rs822.ao Per MT, Rs.671.00 â†’ 67100.00)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[RATE] Starting rate extraction from text (length: {len(text)})")
    
    UNIT = r'(?:MT|M\.?T\.?|TON|TONNE|T|BAG|BAGS|KG|KGS|QUINTAL|QTL|METRIC\s*TON)'
    CURR = r'(?:Rs\.?|â‚¹|INR)\s*'
    # Enhanced amount pattern allowing OCR errors (O, I, l, S, ao) and optional commas/periods
    AMT = r'([0-9OIlSs]{1,5}(?:[,\.\s]?[0-9OIlSs]{1,3})*(?:\.[0-9OIlSsao]+)?)'
    
    patterns = [
        # Most specific first - @ symbol patterns
        (rf'@\s*{CURR}{AMT}\s*(?:Per|P[a-z]{{0,2}})\s*{UNIT}', "@ Rs.XXX Per MT"),
        (rf'@\s*{CURR}{AMT}\s*/\s*{UNIT}', "@ Rs.XXX/MT"),
        # Standard patterns
        (rf'@\s*{CURR}?{AMT}\s*(?:Per|/)\s*{UNIT}\b', "@ Rs.XXX Per/MT word boundary"),
        (rf'(?:Freight|Rate|Price)[^.\n\r]{{0,120}}{CURR}?{AMT}\s*(?:Per|/)\s*{UNIT}\b', "Freight/Rate/Price"),
        (rf'{CURR}{AMT}\s*(?:Per|/)\s*{UNIT}\b', "Rs.XXX Per/MT"),
        (rf'(?:Per|/)\s*{UNIT}\s*[:\-]?\s*{CURR}{AMT}\b', "Per MT: Rs.XXX"),
        (rf'\bRate\s*(?:Per|/)\s*{UNIT}\s*[:\-]?\s*{CURR}?{AMT}\b', "Rate Per MT"),
        # Enhanced patterns for the specific format in the image
        (rf'Limited\s*@\s*{CURR}{AMT}\s*(?:Per|/)\s*{UNIT}', "Limited @ Rs.XXX"),
        (rf'{CURR}{AMT}[.\s]*(?:Per|/)\s*{UNIT}', "Rs.XXX.Per MT (loose)"),
        (rf'@\s*{CURR}{AMT}[.\s]*(?:ao|oo|OO)\s*(?:Per|/)\s*{UNIT}', "@ Rs.XXXao Per MT"),
    ]
    
    for pat, desc in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            amount_str = m.group(1)
            logger.info(f"[RATE] Pattern matched ({desc}): '{m.group(0)[:50]}'")
            logger.info(f"[RATE] Raw amount captured: '{amount_str}'")
            
            # Normalize OCR errors comprehensively
            amount_str = _normalize_ocr_smudge(amount_str)
            # Additional fixes for common rate OCR errors
            amount_str = amount_str.replace('ao', '00').replace('oo', '00').replace('OO', '00')
            
            # OCR sometimes uses European format (comma as decimal separator)
            # Rs.67,100 â†’ 67.100 (replace comma with period)
            # Rs.617,00 â†’ 617.00 (replace comma with period)
            amount_str = amount_str.replace(',', '.')
            
            logger.info(f"[RATE] After normalization: '{amount_str}'")
            
            # Normal money normalization
            normalized = _normalize_money(amount_str)
            if normalized:
                logger.info(f"[RATE] Final rate: {normalized}")
                return normalized
            else:
                logger.warning(f"[RATE] Failed to normalize amount: '{amount_str}'")
    
    logger.warning("[RATE] No rate pattern matched in text")
    # Debug: Show what @ patterns exist
    at_patterns = re.findall(r'@[^@]{0,50}', text, re.IGNORECASE)
    if at_patterns:
        logger.info(f"[RATE] Found @ symbols in text: {at_patterns[:3]}")
    
    # FALLBACK: Very lenient pattern - just Rs + number + MT anywhere nearby
    fallback = re.search(rf'{CURR}([0-9OIlSs,.]+).*?{UNIT}', text, re.IGNORECASE | re.DOTALL)
    if fallback:
        amount_str = fallback.group(1)
        logger.info(f"[RATE] FALLBACK match: '{fallback.group(0)[:100]}'")
        logger.info(f"[RATE] FALLBACK amount: '{amount_str}'")
        
        # Normalize
        amount_str = _normalize_ocr_smudge(amount_str)
        amount_str = amount_str.replace('ao', '00').replace('oo', '00').replace('OO', '00')
        amount_str = amount_str.replace(',', '.')
        
        normalized = _normalize_money(amount_str)
        if normalized:
            logger.info(f"[RATE] FALLBACK final rate: {normalized}")
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
                # extract the portion after the keyword 'destination' on the line
                idx = line.lower().find('destination')
                cand = line[idx + len('destination'):].strip(" :,-")
                break

    if not cand:
        return None

    # Remove noisy trailing tokens and parentheses, keep only letters and spaces
    cand = re.split(
        r'\b(?:DESPATCH|DISPATCH|FROM|BOOKING|STATION|COMMERCIAL|TERMS)\b',
        cand, 1, flags=re.IGNORECASE
    )[0]
    # remove parenthetical content and trim common separators but preserve hyphens/slashes
    cand = cand.split('(')[0].strip(" ,:-")
    cand = cand.strip()

    # Use the conservative cleaning helper and return the cleaned raw candidate.
    cleaned = clean_destination(cand)
    return cleaned


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
        'L': '1',  # Uppercase L to digit 1 (critical for vehicle plates)
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
                                                logger.debug(f"  [E-Way] âœ“ Found via targeted OCR at {angle}Â°: {num}")
                                                return num
                                        
                                        # Try sequences in cleaned text
                                        cleaned = re.sub(r'[^0-9]', '', eway_text)
                                        if len(cleaned) >= 12:
                                            for j in range(len(cleaned) - 11):
                                                candidate = cleaned[j:j+12]
                                                if not _looks_like_datetime(candidate) and len(set(candidate)) > 3:
                                                    logger.debug(f"  [E-Way] âœ“ Found via sequence at {angle}Â°: {candidate}")
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
                                                        logger.debug(f"  [E-Way] âœ“ Found via EWB pattern at {angle}Â°: {num}")
                                                        return num
                                                    
                                    except Exception as e:
                                        logger.debug(f"  [E-Way] OCR at {angle}Â° PSM {psm} failed: {e}")
                                        continue
                    except Exception as e:
                        logger.debug(f"  [E-Way] Rotation {angle}Â° failed: {e}")
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
    
    # Check for hour:minute patterns (23:59 â†’ 2359)
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
    """
    Normalize common OCR errors in vehicle plates - ENHANCED
    Vehicle format: STATE(2) + DISTRICT(1-2) + SERIES(1-3) + NUMBER(3-4)
    Example: TN45BQ0372 = TN + 45 + BQ + 0372
    
    Position-based smart normalization:
    - State (pos 0-1): Always letters
    - District (pos 2-3): Digits only - normalize Oâ†’0, Iâ†’1, Sâ†’5
    - Series (pos 4-5/4-6): Letters only - normalize 8â†’B, 0â†’D for digits in this section
    - Number (pos 6+): Digits only - normalize Oâ†’0, Iâ†’1, Sâ†’5
    """
    if not plate:
        return plate
    
    plate = plate.upper().replace(' ', '')
    
    # Debug: Show what we're working with
    logger.info(f"  [Vehicle] Normalizing: '{plate}' (len={len(plate)})")
    
    # Fix common OCR error: "FN" misread for "TN" (e.g. FN45... -> TN45...)
    if plate.startswith("FN"):
        logger.info(f"  [Vehicle] OCR fix: {plate} -> TN{plate[2:]} (FN->TN)")
        plate = "TN" + plate[2:]
    
    # Fix common OCR error: "118" misread for "18" in district section
    # Example: TN118K7553 â†’ TN18K7553 (extra "1" inserted)
    # Pattern: XX118 (where next char is a letter in series)
    if len(plate) >= 6:
        logger.info(f"  [Vehicle] Checking 118 pattern: plate[2:5]='{plate[2:5]}', plate[5]='{plate[5] if len(plate) > 5 else 'N/A'}'")
        if (plate[2:5] == '118' and 
            len(plate) > 5 and 
            plate[5].isalpha()):
            # Replace 118 with 18
            old_plate = plate
            plate = plate[0:2] + '18' + plate[5:]
            logger.info(f"  [Vehicle] OCR fix: {old_plate} â†’ {plate} (118â†’18 in district)")
        else:
            logger.info(f"  [Vehicle] No 118 fix needed")
    
    # Fix common OCR error: "11B" misread for "18" in district section
    # Example: TN11BK7553 â†’ TN18K7553 (11B should be 18)
    # Pattern: XX11B (where B is followed by a letter in series)
    if len(plate) >= 5:
        # Check if positions 2-4 are "11B" and position 5 is a letter
        if (plate[2:5] == '11B' and 
            len(plate) > 5 and 
            plate[5].isalpha()):
            # Replace 11B with 18
            plate = plate[0:2] + '18' + plate[5:]
            logger.debug(f"  [Vehicle] OCR fix: 11Bâ†’18 (misread district)")
    
    # Fix common OCR error: "1B" misread for "18" in district section when followed by single letter
    # Example: TN1BK7553 â†’ TN18K7553 (1B should be 18)
    elif len(plate) >= 4:
        if (plate[2:4] == '1B' and 
            len(plate) > 4 and 
            plate[4].isalpha()):
            # Check if next char is a letter (series section)
            # This pattern suggests 1B is misread "18"
            plate = plate[0:2] + '18' + plate[4:]
            logger.debug(f"  [Vehicle] OCR fix: 1Bâ†’18 (misread district)")
    
    # Handle standard 10-character plates: XX NN LL NNNN (2+2+2+4)
    if len(plate) == 10:
        state = plate[0:2]        # TN
        district = plate[2:4]      # 45 or 4S
        series = plate[4:6]        # BQ or 8Q or 0A
        number = plate[6:10]       # 0372 or O372
        
        # Normalize district: Oâ†’0, Iâ†’1, Sâ†’5 (digits)
        district_norm = _normalize_ocr_smudge(district)
        
        # REMOVED: Series normalization (8â†’B, 0â†’D, etc.)
        # Reason: OCR extraction is accurate, don't change valid series characters
        # Keep series as-is to preserve correct extraction
        series_norm = series
        
        # Normalize number: Oâ†’0, Iâ†’1, Sâ†’5 (digits)
        number_norm = _normalize_ocr_smudge(number)
        
        result = f"{state}{district_norm}{series_norm}{number_norm}"
        if result != plate:
            logger.debug(f"  [Vehicle] OCR normalization: {plate} -> {result}")
        return result
    
    # Handle 9-character plates: Can be XX N LL NNNN (2+1+2+4) OR XX NN L NNNN (2+2+1+4)
    elif len(plate) == 9:
        state = plate[0:2]
        
        # Check if position 3 is a letter (then it's 2+1+2+4 format)
        # Otherwise if position 3 is a digit, it's 2+2+1+4 format
        if plate[2].isdigit() and plate[3].isdigit():
            # Format: XX NN L NNNN (2+2+1+4) - e.g., TN18K7553
            district = plate[2:4]      # 18
            series = plate[4:5]        # K
            number = plate[5:9]        # 7553
            
            district_norm = _normalize_ocr_smudge(district)
            # Series is single letter - still apply letter normalization
            series_norm = (series
                          .replace('8', 'B')
                          .replace('0', 'D')
                          .replace('1', 'I')
                          .replace('5', 'S'))
            number_norm = _normalize_ocr_smudge(number)
            
            result = f"{state}{district_norm}{series_norm}{number_norm}"
        else:
            # Format: XX N LL NNNN (2+1+2+4) - e.g., KA1AN0922
            district = plate[2:3]      # 1
            series = plate[3:5]        # AN
            number = plate[5:9]        # 0922
            
            district_norm = _normalize_ocr_smudge(district)
            series_norm = (series
                          .replace('8', 'B')
                          .replace('0', 'D')
                          .replace('1', 'I')
                          .replace('5', 'S'))
            number_norm = _normalize_ocr_smudge(number)
            
            result = f"{state}{district_norm}{series_norm}{number_norm}"
        
        if result != plate:
            logger.debug(f"  [Vehicle] OCR normalization: {plate} -> {result}")
        return result
    
    # Handle 11-character plates: XX NN LLL NNNN (2+2+3+4)
    elif len(plate) == 11:
        state = plate[0:2]
        district = plate[2:4]
        series = plate[4:7]
        number = plate[7:11]
        
        district_norm = _normalize_ocr_smudge(district)
        series_norm = (series
                      .replace('8', 'B')
                      .replace('0', 'D')
                      .replace('1', 'I')
                      .replace('5', 'S'))
        number_norm = _normalize_ocr_smudge(number)
        
        result = f"{state}{district_norm}{series_norm}{number_norm}"
        if result != plate:
            logger.debug(f"  [Vehicle] OCR normalization: {plate} -> {result}")
        return result
    
    # For other lengths, try regex pattern matching
    match = re.match(r'^([A-Z]{2})([0-9OIlSs]{1,2})([A-Z0-9]{1,3})([0-9OIlSs]{3,4})$', plate)
    if match:
        state = match.group(1)
        district = match.group(2)
        series = match.group(3)
        number = match.group(4)
        
        district_norm = _normalize_ocr_smudge(district)
        series_norm = (series
                      .replace('8', 'B')
                      .replace('0', 'D')
                      .replace('1', 'I')
                      .replace('5', 'S'))
        number_norm = _normalize_ocr_smudge(number)
        
        result = f"{state}{district_norm}{series_norm}{number_norm}"
        if result != plate:
            logger.debug(f"  [Vehicle] OCR normalization (regex): {plate} -> {result}")
        return result
    
    return plate


def _fix_oversized_vehicle(plate: str) -> str:
    """
    Fix 11+ character vehicle numbers by analyzing structure and removing duplicates.
    
    Indian vehicle format: SS DD LL NNNN
    - SS = 2 letters (State: TN, KA, MH)
    - DD = 1-2 digits (District: 5, 05, 23)
    - LL = 1-2 letters (Series: A, AM, AY)
    - NNNN = 4 digits (Number: 5290)
    
    Total = 8-10 characters maximum.
    
    If length > 10, OCR likely duplicated a similar-looking character at boundaries:
    - S ↔ 5
    - O ↔ 0, D
    - I ↔ 1, L
    - B ↔ 8
    
    Example: TN23AMS5290 (11 chars) → TN23AM5290 (S is duplicate of 5)
    """
    if not plate:
        return plate
    
    plate = plate.upper().replace(' ', '')
    
    # Only process if length > 10 (oversized)
    if len(plate) <= 10:
        return plate
    
    logger.info(f"  [Vehicle] Fixing oversized plate ({len(plate)} chars): {plate}")
    
    # Similar character pairs (letter ↔ digit mappings)
    LETTER_TO_DIGIT = {'S': '5', 'O': '0', 'D': '0', 'I': '1', 'L': '1', 'B': '8'}
    DIGIT_TO_LETTER = {'5': 'S', '0': 'O', '1': 'I', '8': 'B'}
    
    # Parse the plate structure: SS (2 letters) + rest
    if len(plate) < 2 or not plate[:2].isalpha():
        logger.warning(f"  [Vehicle] Invalid plate format (no state code): {plate}")
        return plate
    
    state = plate[:2]  # Always 2 letters
    rest = plate[2:]
    
    # Find where digits start (district section)
    district_start = 0
    while district_start < len(rest) and rest[district_start].isdigit():
        district_start += 1
        if district_start >= 2:  # Max 2 district digits
            break
    
    # If no digits found, try to find digit-like letters at start
    if district_start == 0:
        # Check if first char is a letter that looks like a digit
        if rest[0] in LETTER_TO_DIGIT:
            # Could be O (looks like 0) or similar
            logger.info(f"  [Vehicle] First char '{rest[0]}' looks like digit, treating as district part")
            district_start = 1
            if len(rest) > 1 and (rest[1].isdigit() or rest[1] in LETTER_TO_DIGIT):
                district_start = 2
    
    district = rest[:district_start] if district_start > 0 else ""
    after_district = rest[district_start:]
    
    # Find where series (letters) section is
    series_end = 0
    while series_end < len(after_district) and after_district[series_end].isalpha():
        series_end += 1
        if series_end >= 3:  # Max 2-3 series letters (3 means possible duplicate)
            break
    
    series = after_district[:series_end]
    number = after_district[series_end:]
    
    logger.info(f"  [Vehicle] Parsed: State={state}, District={district}, Series={series}, Number={number}")
    logger.info(f"  [Vehicle] Lengths: State=2, District={len(district)}, Series={len(series)}, Number={len(number)}")
    
    # Calculate expected vs actual length
    # Valid: State(2) + District(1-2) + Series(1-2) + Number(4) = 8-10
    total_len = 2 + len(district) + len(series) + len(number)
    
    # Check which section is oversized
    fixed = False
    
    # Case 1a: Series has 3+ letters AND first letter looks like last digit of district
    # Example: KA01LAN0922 -> L looks like 1, so LAN should be AN (remove first L)
    if len(series) >= 3 and len(district) >= 1:
        first_series_char = series[0]
        last_district_char = district[-1]
        
        # Check if first series letter looks like last digit of district
        if first_series_char in LETTER_TO_DIGIT:
            expected_digit = LETTER_TO_DIGIT[first_series_char]
            if last_district_char == expected_digit:
                # Remove the duplicate letter from series start
                series = series[1:]
                logger.info(f"  [Vehicle] Removed duplicate '{first_series_char}' from series start (looks like '{expected_digit}')")
                fixed = True
    
    # Case 1b: Series has 3+ letters AND last letter looks like first digit of number
    # Example: AMS should be AM (S is duplicate of 5 from number)
    if not fixed and len(series) >= 3 and len(number) >= 4:
        last_series_char = series[-1]
        first_num_char = number[0] if number else ""
        
        # Check if last series letter looks like first digit of number
        if last_series_char in LETTER_TO_DIGIT:
            expected_digit = LETTER_TO_DIGIT[last_series_char]
            if first_num_char == expected_digit or first_num_char == last_series_char:
                # Remove the duplicate letter from series
                series = series[:-1]
                logger.info(f"  [Vehicle] Removed duplicate '{last_series_char}' from series (looks like '{expected_digit}')")
                fixed = True
    
    # Case 2: District has 3+ digits (should be max 2)
    if not fixed and len(district) >= 3:
        last_district_char = district[-1]
        first_series_char = series[0] if series else ""
        
        # Check if last district digit looks like first letter of series
        if last_district_char in DIGIT_TO_LETTER:
            expected_letter = DIGIT_TO_LETTER[last_district_char]
            if first_series_char == expected_letter or first_series_char == last_district_char:
                # Remove the duplicate digit from district
                district = district[:-1]
                logger.info(f"  [Vehicle] Removed duplicate '{last_district_char}' from district (looks like '{expected_letter}')")
                fixed = True
    
    # Case 3: Number has 5+ digits (should be max 4)
    if not fixed and len(number) >= 5:
        # Check if first digit of number is duplicate of last series letter
        first_num_char = number[0]
        last_series_char = series[-1] if series else ""
        
        if first_num_char in DIGIT_TO_LETTER:
            expected_letter = DIGIT_TO_LETTER[first_num_char]
            if last_series_char == expected_letter:
                # Remove the duplicate digit from number
                number = number[1:]
                logger.info(f"  [Vehicle] Removed duplicate '{first_num_char}' from number (looks like '{expected_letter}')")
                fixed = True
    
    # Case 4: Check for adjacent similar chars anywhere in boundary regions
    if not fixed:
        # Check district-series boundary
        if district and series:
            last_d = district[-1]
            first_s = series[0]
            if (last_d in DIGIT_TO_LETTER and DIGIT_TO_LETTER[last_d] == first_s) or \
               (first_s in LETTER_TO_DIGIT and LETTER_TO_DIGIT[first_s] == last_d):
                # Remove one of them - prefer keeping the structure
                if len(district) > 1:
                    district = district[:-1]
                    logger.info(f"  [Vehicle] Removed duplicate at district-series boundary")
                else:
                    series = series[1:]
                    logger.info(f"  [Vehicle] Removed duplicate at series start")
                fixed = True
        
        # Check series-number boundary
        if not fixed and series and number:
            last_s = series[-1]
            first_n = number[0]
            if (last_s in LETTER_TO_DIGIT and LETTER_TO_DIGIT[last_s] == first_n) or \
               (first_n in DIGIT_TO_LETTER and DIGIT_TO_LETTER[first_n] == last_s):
                # Remove one of them
                if len(series) > 1:
                    series = series[:-1]
                    logger.info(f"  [Vehicle] Removed duplicate at series-number boundary")
                else:
                    number = number[1:]
                    logger.info(f"  [Vehicle] Removed duplicate at number start")
                fixed = True
    
    # Reconstruct the plate
    result = state + district + series + number
    
    # If still oversized and we couldn't fix, log warning
    if len(result) > 10:
        if fixed:
            # Try again recursively
            logger.info(f"  [Vehicle] Still oversized ({len(result)} chars), trying again...")
            result = _fix_oversized_vehicle(result)
        else:
            logger.warning(f"  [Vehicle] Could not fix plate, still {len(result)} chars: {result}")
    
    if result != plate:
        logger.info(f"  [Vehicle] Fixed: {plate} → {result}")
    
    return result


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
        # STRICT patterns: District=1-2 digits, Series=LETTERS ONLY (no digits allowed)
        # This prevents matching "TN118K7553" as "TN + 11 + 8K + 7553"
        re.compile(r'Vehicle\s*No\.?\s*/?\s*Wagon\s*NO?\.?\s*[:\-]?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Vehicle\s*No\.?\s*[:\-/]?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Wagon\s*NO?\.?\s*[:\-/]?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})', re.IGNORECASE),
        # With spaces in the vehicle number
        re.compile(r'Vehicle\s*No\.?\s*/?\s*Wagon\s*NO?\.?\s*[:\-]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Vehicle\s*No\.?\s*[:\-/]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', re.IGNORECASE),
        re.compile(r'Wagon\s*NO?\.?\s*[:\-/]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', re.IGNORECASE),
    ]
    
    # Robust plate validation patterns
    PLATE_PATTERNS = [
        re.compile(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$', re.IGNORECASE), # Clean plates
        re.compile(r'^[A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4}$',re.IGNORECASE), # With spaces
        # Allow OCR errors: digits in series, O/I/l/S in number sections
        re.compile(r'^[A-Z]{2}[0-9OIlSs]{1,2}[A-Z0-9]{1,3}[0-9OIlSs]{3,4}$', re.IGNORECASE),
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
                return _fix_oversized_vehicle(result)
    
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
                                return _fix_oversized_vehicle(result)
                    
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
                                        return _fix_oversized_vehicle(result)
    
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
            return _fix_oversized_vehicle(result)
        
        result = candidates[0]
        logger.info(f"  [Vehicle] ✓ Found via global search: {result}")
        return _fix_oversized_vehicle(result)
    
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
    - Render PDF at DPI 300
    - Run Tesseract OCR for ALL fields EXCEPT Delivery Address
    
    PASS 2 (delivery_address.py):
    - Focused PaddleOCR scan for Delivery Address only
    
    Returns: Complete RAW data dictionary with all fields
    """
    
    # ============================================
    # SETUP: Detect Tesseract and Poppler
    # ============================================
    tess = _detect_tesseract(tesseract_cmd)
    logger.info("âœ“ Using Tesseract: %s", tess)
    
    poppler = _detect_poppler(poppler_path)
    if poppler:
        logger.info("âœ“ Using Poppler: %s", poppler)

    # ============================================
    # PASS 1: Render PDF and Run Tesseract OCR
    # ============================================
    logger.info("=" * 60)
    logger.info("PASS 1: Tesseract OCR @ DPI 300 (Optimized for speed)")
    logger.info("=" * 60)
    
    try:
        # OPTIMIZED: Reduced DPI from 300 to 300 for 4x faster rendering
        # DPI 300 is still excellent quality for text OCR
        if poppler:
            pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler)
        else:
            pages = convert_from_path(pdf_path, dpi=300)
        logger.info("âœ“ Rendered %d page(s) from PDF", len(pages))
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
    logger.info("âœ“ OCR completed. Total text length: %d characters", len(text))

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
    if not consignee:
        # Regex fallback: capture block after Recipient/Address header up to GSTIN/Place/EMAIL
        try:
            m = re.search(r'(?:Recipient|Address)[^\S\r\n]*[:\-]*\s*\n([\s\S]{1,300}?)\n(?=\s*(?:Place of supply|Place of Supply|GSTIN|GST|State:|State Code:|Recipient PO|EMAIL))', text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                # remove trailing address/number fragments (e.g., '11 FLOOR NO 979')
                cand = re.split(r'\s+\d[\d\s/\-\.]*', cand, maxsplit=1)[0]
                cand = re.sub(r'\s+', ' ', cand).strip(' ,:\n')
                cand_clean = clean_consignee(cand)
                if cand_clean:
                    consignee = cand_clean
                    logger.info("  Consignee (regex fallback): %s", consignee)
        except Exception:
            pass

    consignee = clean_consignee(consignee)
    # If our strict cleaning rejected the candidate, try the salvage helper
    consignee_focus_for_ai = None
    if not consignee and _salvage_consignee:
        try:
            logger.info("[CONSIGNEE] No valid consignee â€” attempting focused salvage helper")
            # Prefer header-nearby lines if available to avoid picking unrelated text
            header_re = re.compile(r'(?:Name\s*(?:&|and)\s*Address\s*(?:of|0f|o1|01|:)?\s*(?:Recipient|Consignee))\s*:?', re.IGNORECASE)
            lines = (text or "").splitlines()
            focused_block = None
            focused_block_lines_idxs = []
            for idx, ln in enumerate(lines):
                if header_re.search(ln):
                    # collect a few following lines that likely contain the company block
                    block_lines = []
                    for j in range(idx+1, min(idx+6, len(lines))):
                        cand = (lines[j] or '').strip()
                        if not cand:
                            if block_lines:
                                break
                            continue
                        block_lines.append(cand)
                        focused_block_lines_idxs.append((cand, j))
                    if block_lines:
                        focused_block = '\n'.join(block_lines)
                        break

            # If no header block, fall back to searching for lines with company suffix tokens
            if not focused_block:
                suffix_search = re.compile(r'\b(PVT|LTD|PRIVATE|LIMITED|LLP|INC|CO)\b', re.IGNORECASE)
                candidate_lines = [ln.strip() for ln in lines if suffix_search.search(ln)]
                if candidate_lines:
                    # take the first few candidate lines (keep indices)
                    sel = []
                    for i, ln in enumerate(lines):
                        if suffix_search.search(ln):
                            sel.append((ln.strip(), i))
                            if len(sel) >= 4:
                                break
                    focused_block_lines_idxs = sel
                    focused_block = '\n'.join([t[0] for t in sel])

            # Select highest low-alpha candidate from the focused block (or full text)
            to_pass = None
            scan_lines = []
            if focused_block:
                consignee_focus_for_ai = focused_block
                logger.info("[CONSIGNEE] Scanning focused block for best low-alpha candidate")
                # prefer to keep original line indices so we can build a small context
                if focused_block_lines_idxs:
                    scan_lines = [(ln, idx) for (ln, idx) in focused_block_lines_idxs if ln]
                else:
                    scan_lines = [(ln.strip(), None) for ln in focused_block.splitlines() if ln.strip()]
            else:
                logger.info("[CONSIGNEE] No focused block found; scanning full text for best candidate")
                scan_lines = [(ln.strip(), i) for i, ln in enumerate((text or "").splitlines()) if ln.strip()]

            candidates = []
            for ln_item in scan_lines:
                ln, ln_idx = (ln_item if isinstance(ln_item, tuple) else (ln_item, None))
                if not re.search(r'[A-Za-z]', ln):
                    continue
                total_vis = len(re.sub(r'\s+', '', ln)) or 1
                alpha_ratio = sum(1 for c in ln if c.isalpha()) / total_vis
                # collect all potentially noisy lines
                if alpha_ratio < 0.75 or re.search(r'\d{2,}|/', ln):
                    candidates.append((alpha_ratio, ln, ln_idx))

            # Prefer true low-alpha lines first (alpha < 0.75). If present, choose the one with highest alpha among them.
            low_alpha = [c for c in candidates if c[0] < 0.75]
            chosen = None
            if low_alpha:
                low_alpha.sort(key=lambda x: x[0], reverse=True)
                chosen = low_alpha[0]
            elif candidates:
                # fallback: choose the candidate with highest alpha among digit-containing/other candidates
                candidates.sort(key=lambda x: x[0], reverse=True)
                chosen = candidates[0]

            if chosen:
                top_alpha, top_candidate, top_idx = chosen
                logger.info("[CONSIGNEE] Selected candidate for AI salvage (alpha=%.2f): %s", top_alpha, top_candidate[:200])
                # Build a small context: the focused block (if present) is still preferred because
                # it contains adjacent lines (including suffix-only lines). Otherwise, build a
                # short window around the candidate in the full text using the line index.
                if focused_block:
                    to_pass = focused_block
                elif top_idx is not None:
                    full_lines = (text or "").splitlines()
                    a = max(0, top_idx-2)
                    b = min(len(full_lines), top_idx+3)
                    to_pass = '\n'.join([l.strip() for l in full_lines[a:b] if l.strip()])
                else:
                    to_pass = top_candidate
            else:
                to_pass = focused_block if focused_block else text

            salvage = _salvage_consignee(to_pass)

            if salvage:
                # Reject obviously noisy salvage results (payment text, PAN, UPI, etc.)
                noise_re = re.compile(r'\b(PAYMENT|PLACE OF SUPPLY|PAN|UPI|RUPAY|QR CODE|PAYMENT CAN ALSO BE|BHIM|DEBIT|CARD)\b', re.IGNORECASE)
                if noise_re.search(salvage):
                    logger.info("[CONSIGNEE] Salvage returned noisy/non-company text, rejecting: %s", salvage[:140])
                    # If the focused block produced noisy output, try a targeted salvage on the single-line candidate
                    try:
                        if focused_block and 'top_candidate' in locals():
                            logger.info("[CONSIGNEE] Retrying salvage using single-line candidate")
                            salvage2 = _salvage_consignee(top_candidate)
                            if salvage2 and not noise_re.search(salvage2):
                                # If salvage2 looks acceptable, append suffix from focused_block if present
                                final_salv = salvage2
                                try:
                                    # search focused_block lines for suffix tokens
                                    for ln, _idx in (focused_block_lines_idxs or []):
                                        if re.search(r'\bPVT\b|\bPVT\.|\bPVT\s+LTD|PRIVATE\s+LIMITED|\bLTD\b|\bLLP\b', ln, re.IGNORECASE):
                                            if not re.search(r'\b(PVT|PVT\.|PVT\s+LTD|PRIVATE\s+LIMITED|LTD|LLP)\b', final_salv, re.IGNORECASE):
                                                if re.search(r'\bPVT\b|\bPVT\.', ln, re.IGNORECASE):
                                                    final_salv = final_salv + ' Pvt Ltd'
                                                elif re.search(r'PRIVATE\s+LIMITED', ln, re.IGNORECASE):
                                                    final_salv = final_salv + ' Private Limited'
                                                elif re.search(r'\bLTD\b|\bLIMITED\b', ln, re.IGNORECASE):
                                                    final_salv = final_salv + ' Ltd'
                                                break
                                except Exception:
                                    pass
                                consignee = final_salv
                                logger.info("  Consignee (salvaged): %s", consignee)
                    except Exception:
                        logger.exception("[CONSIGNEE] Salvage helper retry failed")
                else:
                    consignee = salvage
                    logger.info("  Consignee (salvaged): %s", consignee)
        except Exception:
            logger.exception("[CONSIGNEE] Salvage helper failed")

    logger.info("  Consignee: %s", consignee or "NOT FOUND")
    
    consignor = "UltraTech Cement Limited" if "ULTRATECH CEMENT LIMITED" in (text or "").upper() else None
    logger.info("  Consignor: %s", consignor or "NOT FOUND")
    
    weight, weight_method = extract_quantity_weight(originals, text)
    logger.info("  Weight: %s (method: %s)", weight or "NOT FOUND", weight_method or "N/A")
    
    content_name, content_method = extract_material_code_global(text)
    if not content_name:
        # Default to PPC if no specific material code found
        content_name = "PPC"
        logger.info("  Content Name: %s (defaulted to PPC)", content_name)
    else:
        logger.info("  Content Name: %s", content_name)
    
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
    
    # Detect goods type: BAG (includes LOOSE), BULK, or None
    goods_type = "BAG" if re.search(r'\b(?:BAGS?|LOOSE)\b', text, re.IGNORECASE) else (
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

    # --------------------------------------------
    # AI-assisted Consignee refinement (targeted)
    # If the extracted consignee is missing, very short, or clearly a generic suffix
    # (e.g. just 'Pvt Ltd'), ask the AI refiner to extract a better value from the
    # full OCR text. This is conservative and only used when the simple extractor
    # is not confident.
    try:
        try_call_ai = False
        cand = raw_data.get("Consignee")
        if not cand:
            try_call_ai = True
        else:
            # Generic / garbage candidates
            if re.match(r'^\s*(PVT\.?\s*LTD\.?|LTD\.?|PRIVATE\.?|CO\.?\b).*', cand or '', re.IGNORECASE):
                try_call_ai = True
            # too short or obviously wrong
            if isinstance(cand, str) and len(cand.strip()) < 6:
                try_call_ai = True
            # suspicious OCR artifacts: consecutive repeated characters (e.g., 'Liiimited')
            # RELAXED: Require 3+ repeats to avoid flagging valid names like "KANNAPPA"
            if isinstance(cand, str) and re.search(r'([A-Za-z])\1\1', cand):
                try_call_ai = True

        # Check environment toggle: only use AI for consignee when enabled
        use_ai_flag = os.environ.get('CONSIGNEE_USE_AI', '1').lower() in ('1', 'true', 'yes')
        if try_call_ai and use_ai_flag and _HAS_AI_REFINER and _refine_consignee:
            logger.info("[AI CONSIGNEE] Running AI-assisted consignee refinement...")
            # Prefer passing a focused candidate (near header or suffix lines) to avoid model guessing unrelated entities
            ai_candidate = cand or consignee_focus_for_ai or ''
            ai_res = _refine_consignee(ai_candidate, text)
            logger.info(f"[AI CONSIGNEE] AI result: refined={ai_res.get('refined')} confidence={ai_res.get('confidence')}")
            if ai_res and ai_res.get('consignee'):
                # Accept AI value only if it actually refined and produced a suitable company name,
                # or if it's very high confidence and passes basic content checks.
                conf = float(ai_res.get('confidence') or 0.0)

                def _is_suffix_only_local(s: str) -> bool:
                    if not s:
                        return True
                    words = [w.strip(".,()[]") for w in re.split(r'\s+|[,|\\|/]', s) if w.strip()]
                    if not words:
                        return True
                    suffixes = {"pvt", "ltd", "private", "limited", "llp", "co", "company", "inc", "corp", "gmbh"}
                    core = [re.sub(r'[^A-Za-z]', '', w).lower() for w in words]
                    if all((not c) or (c in suffixes) or (len(c) <= 2) for c in core):
                        return True
                    return False

                candidate_ai = (ai_res.get('consignee') or '').strip()
                accept = False
                if ai_res.get('refined'):
                    # AI claims it refined; accept only if not suffix-only
                    if not _is_suffix_only_local(candidate_ai):
                        accept = True
                else:
                    # If AI didn't mark 'refined', only accept very-high-confidence and not suffix-only
                    if conf >= 0.90 and not _is_suffix_only_local(candidate_ai):
                        accept = True

                if accept:
                    new_val = candidate_ai
                    raw_data['Consignee'] = new_val
                    raw_data['Billing Party'] = new_val
                    logger.info("[AI CONSIGNEE] Updated Consignee from AI: %s", new_val)
                else:
                    logger.info("[AI CONSIGNEE] AI returned unsuitable/low-confidence result (%.2f), keeping original: %s", conf, cand)
            else:
                logger.info("[AI CONSIGNEE] AI did not return a better consignee; keeping original.")
    except Exception:
        logger.debug("[AI CONSIGNEE] AI refinement failed", exc_info=True)

    # ============================================
    # PASS 2: Robust Delivery Address Extraction (Internal)
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.info("PASS 2: Robust Delivery Address Extraction (Internal)")
    logger.info("=" * 60)
    
    try:
        # Use Page 1 for delivery address (standard for Format 1)
        if originals:
            da_robust = extract_delivery_address_robust(originals[0], page_num=1, debug=True)
            if da_robust:
                # Ensure single-line clean output (Address usually comes multiline from OCR)
                da_robust = da_robust.replace('\n', ', ').strip()
                raw_data["Delivery Address"] = da_robust
                logger.info("✓ Delivery Address extracted successfully (Robust)")
            else:
                logger.warning("⚠ Delivery Address not found via robust method")
        else:
             logger.warning("âš  No page images available for delivery address extraction")
             
    except Exception as e:
        logger.error("âœ— Delivery Address extraction failed: %s", e, exc_info=True)
        logger.warning("  Delivery Address will remain NULL in output")

    # ============================================
    # SAVE RAW DATA (Optional)
    # ============================================
    if save_raw_path:
        try:
            os.makedirs(os.path.dirname(save_raw_path), exist_ok=True)
            with open(save_raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            logger.info("\nâœ“ RAW JSON saved: %s", save_raw_path)
        except Exception as e:
            logger.warning("âš  Failed to save RAW JSON %s: %s", save_raw_path, e)

    # ============================================
    # AI REFINEMENT - DISABLED (Extraction is already accurate)
    # ============================================
    # NOTE: AI refinement for all fields has been disabled
    # Delivery Address still uses AI formatting via delivery_address.py
    logger.info("\n" + "=" * 60)
    logger.info("AI REFINEMENT: Skipped (using direct extraction)")
    logger.info("=" * 60)
    logger.info("  All fields extracted directly from OCR")
    logger.info("  Delivery Address formatted by AI (via delivery_address.py)")
    
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
            logger.info("âœ“ Data transformation completed:")
            for change in transformation_result["changes"]:
                logger.info(f"  â€¢ {change['field']}: '{change['from']}' â†’ '{change['to']}'")
            # Update raw_data with transformed values
            raw_data = transformation_result["data"]
        else:
            logger.info("âœ“ No data transformations needed")
    
    except ImportError as e:
        logger.warning("âš  Data transformation module not available: %s", e)
        logger.warning("  Skipping data transformation step")
    except Exception as e:
        logger.error("âœ— Data transformation failed: %s", e, exc_info=True)
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
