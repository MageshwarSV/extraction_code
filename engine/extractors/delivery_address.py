# engine/extractors/delivery_address.py
# -------------------------------------------------------------
# PASS 2: Delivery Address Extractor (Tesseract-only, RIGHT-SIDE ONLY)
# - Ensures header fragments (e.g. "Name & Address of Delivery") are removed
# - Saves the detected crop image to a local folder for debugging
# - Performs alignment correction and reorders/join words using OpenCV + Tesseract
# - Performs letter-wise image-verified merge of split/jumbled tokens (fixes Kan, galam -> Kangalam)
# - Returns a structured dict and a backward-compatible single-line string.
# -------------------------------------------------------------

import os
import re
import time
import json
import logging
import platform
from typing import Optional, List, Dict, Tuple, Any
from difflib import SequenceMatcher

from PIL import Image
import numpy as np

# pdf2image for PDFs
try:
    from pdf2image import convert_from_path
    _HAS_PDF2IMG = True
except Exception:
    _HAS_PDF2IMG = False

# pytesseract required
try:
    import pytesseract
    from pytesseract import Output as TessOutput
    _HAS_TESS = True
except Exception as e:
    _HAS_TESS = False
    raise RuntimeError(f"pytesseract is required but not available: {e}")

# OpenCV optional (better crop heuristics + alignment)
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

# try to import local ai helper (engine.extractors.ai)
try:
    # prefer package import if running as package
    from engine.extractors import ai as ai_client
except Exception:
    try:
        import engine.extractors.ai as ai_client  # type: ignore
    except Exception:
        try:
            # last resort: relative import (if running file directly)
            from . import ai as ai_client  # type: ignore
        except Exception:
            ai_client = None

# -------------------------------------------------------------
# Logging
# -------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# -------------------------------------------------------------
# Timing helper
# -------------------------------------------------------------
def t() -> float:
    return time.time()

def dt(start: float) -> float:
    return t() - start

# -------------------------------------------------------------
# Crop save directory (change if needed)
# -------------------------------------------------------------
DEFAULT_CROP_DIR = r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-main\crop"

def _ensure_crop_dir(path: Optional[str] = None) -> str:
    d = path or DEFAULT_CROP_DIR
    try:
        os.makedirs(d, exist_ok=True)
    except Exception as e:
        logger.warning("Could not create crop dir %s: %s", d, e)
    return d

def _save_crop(crop_img: Image.Image, prefix: str = "crop", page_idx: Optional[int] = None, crop_dir: Optional[str] = None) -> str:
    d = _ensure_crop_dir(crop_dir)
    ts = int(time.time() * 1000)
    ppart = f"_p{page_idx}" if page_idx is not None else ""
    fname = f"{prefix}{ppart}_{ts}.png"
    full = os.path.join(d, fname)
    try:
        crop_img.convert("RGB").save(full)
        logger.info("Saved crop image: %s", full)
    except Exception as e:
        logger.warning("Failed to save crop %s: %s", full, e)
    return full

# -------------------------------------------------------------
# Tuning constants for merge heuristics
# -------------------------------------------------------------
MERGE_SIM_THRESHOLD = 0.78   # similarity threshold for letter-wise match (0..1)
MERGE_SHORT_TOKEN_MAX_LEN = 5  # treat short tokens as suspicious candidate parts
MERGE_MAX_GAP_RATIO = 0.45    # if horizontal gap < (avg_char_w * ... ) consider join
MERGE_DEBUG_SAVE = True       # save debug crops for merged candidates (if crop_save_dir given)

# -------------------------------------------------------------
# Regex constants
# -------------------------------------------------------------
HDR_DELIVERY_RE = re.compile(
    r'(Name\s*[&\-]*\s*Address\s*of\s*(?:D[ie]liv[e]?ry|penvesy)|Name\s*and\s*Address\s*of\s*(?:D[ie]liv[e]?ry|penvesy)|Address\s*of\s*(?:D[ie]liv[e]?ry|penvesy)|D[ie]liv[e]?ry\s*Address|Deliver\s*to|Ship\s*to|D[ie]liv[e]?ry\s*:|penvesy\s*:|Name.*?(?:D[ie]liv[e]?ry|penvesy))',
    re.IGNORECASE
)
HDR_RECIPIENT_RE = re.compile(
    r'(Name\s*&\s*Address\s*of\s*(?:Recipient|Consignee)|Name\s*and\s*Address\s*of\s*(?:Recipient|Consignee))',
    re.IGNORECASE
)
_HDR_FRAGMENTS = re.compile(
    r'(Name\s*(?:&|and)?\s*Address\s*(?:of|af|ad|o[f])?(?:\s*of)?\s*(?:Delivery|Deliver|Recipient|Consignee)|Address\s*of\s*Delivery|Delivery\s*Address|Deliver\s*to|Ship\s*to)',
    re.IGNORECASE
)

HDR_STRIP_GLOBAL = re.compile(
    r'\b(?:Name(?:\s*[:\-]?)?\s*(?:&|and)?\s*Address(?:\s*(?:of|af|ad|o[f])?)?(?:\s*of)?\s*(?:Delivery|Deliver|Recipient|Consignee)?)[\s,:;\-]*',
    re.IGNORECASE
)

STOP_TOKENS = re.compile(
    r'\b(?:GSTIN|GST|STATE\s*CODE|PLACE\s*OF\s*SUPPLY|PHONE|MOBILE|EMAIL|PAN|PO\s*NO|RECIPIENT\s*CODE|INVOICE|AMOUNT|TOTAL|IRN|EWB|BILL\s*NO|SEGMENT)\b',
    re.IGNORECASE
)

PAGE_NOISE_TOKENS = re.compile(
    r'\b(TAX\s*INVOICE|EWB\s*No|Invoice\s*No|Original\s*for\s*Consignee|Original\s*for|Invoice\s*Date|UltraTech|TAX INVOICE|Total\s*Invoice)\b',
    re.IGNORECASE
)

HEADER_STRIP = re.compile(
    r'(?:Name\s*&\s*Address\s*of\s*(?:Delivery|Recipient|Consignee)|Address\s*of\s*Delivery|Delivery\s*Address|Deliver\s*to|Ship\s*to)\s*[:\-]?\s*',
    re.IGNORECASE
)

PINCODE = re.compile(r'\b[1-9][0-9]{5}\b')

# -------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------
def _fix_common_ocr(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    s = s.replace('|', ',')
    s = s.replace('\t', ' ')
    s = re.sub(r'\s{2,}', ' ', s)
    s = re.sub(r'\bDNO\b', 'D NO', s, flags=re.IGNORECASE)
    s = re.sub(r'\bD\s+(?=\d)', 'D NO ', s, flags=re.IGNORECASE)
    s = re.sub(r'\bNO\s*[:\-]?\s*(?=\w)', 'NO: ', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*,\s*,+', ', ', s)
    s = s.strip(' ,;:-')
    return s

def _canon_upper(s: str) -> str:
    return re.sub(r'[^A-Z0-9 ]+', '', s.upper()) if s else ""

def _dedupe_lines(lines: List[str]) -> List[str]:
    start = t()
    seen = set()
    out = []
    for ln in lines:
        key = _canon_upper(ln)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(ln.strip())
    logger.debug("dedupe_lines: input=%d output=%d time=%.4fs", len(lines), len(out), dt(start))
    return out

def _is_noise_line(ln: str) -> bool:
    if not ln:
        return True
    if PAGE_NOISE_TOKENS.search(ln):
        return True
    if len(ln.strip()) < 2:
        return True
    if re.fullmatch(r'[-\s\W]+', ln):
        return True
    if re.match(r'^(Particulars|Quantity|Amount|HSN|No of Packages|Total|Tax)', ln, re.IGNORECASE):
        return True
    return False

def _strip_header_fragments_keep_rest(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    s0 = text
    st = t()
    s = HEADER_STRIP.sub('', s0).strip()
    s = _HDR_FRAGMENTS.sub('', s).strip()
    s = re.sub(r'^[\s,:\-]+', '', s)
    s = re.sub(r'\s{2,}', ' ', s)
    s = s.strip(' ,:-') if s else None
    logger.debug("strip_header_fragments_keep_rest: in='%s' out='%s' time=%.4fs", s0, s, dt(st))
    return s

def _remove_header_fragments_globally(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    st = t()
    s = text
    prev = None
    for i in range(3):
        prev = s
        s = HDR_STRIP_GLOBAL.sub('', s)
        s = re.sub(r'^[\s,:\-]+', '', s)
        s = re.sub(r'\s{2,}', ' ', s)
        if s == prev:
            break
    s = re.sub(r'\s*,\s*,+', ', ', s)
    s = s.strip(' ,;:-')
    s = s or None
    logger.debug("remove_header_fragments_globally: time=%.4fs", dt(st))
    return s

def _clean_delivery_header_words(text: Optional[str]) -> Optional[str]:
    """
    Aggressively remove header words like 'name', 'of', '&', 'delivery', 'address'
    from the final delivery address text.
    """
    if not text:
        return text
    st = t()
    s = text
    
    # Remove common header words (case-insensitive, with word boundaries)
    # Also handle variations with commas, colons, hyphens
    header_words = re.compile(
        r'\b(?:name|of|and|address|delivery|deliver|recipient|consignee|ship|to)\b[\s,:;\-]*',
        re.IGNORECASE
    )
    
    # Also remove standalone '&' symbols
    s = re.sub(r'\s*&\s*', ' ', s)
    
    # Remove the header words (iteratively to handle multiple occurrences)
    prev = None
    for i in range(3):
        prev = s
        s = header_words.sub('', s)
        s = re.sub(r'^[\s,:\-]+', '', s)  # Clean leading punctuation
        s = re.sub(r'[\s,:\-]+$', '', s)  # Clean trailing punctuation
        s = re.sub(r'\s{2,}', ' ', s)     # Collapse multiple spaces
        if s == prev:
            break
    
    # Final cleanup: remove duplicate commas and clean edges
    s = re.sub(r'\s*,\s*,+', ', ', s)
    s = s.strip(' ,;:-')
    s = s or None
    
    logger.debug("clean_delivery_header_words: in='%s' out='%s' time=%.4fs", text[:50] if text else '', s[:50] if s else '', dt(st))
    return s

# -------------------------------------------------------------
# Tesseract helpers (deep timing)
# -------------------------------------------------------------
def _image_to_tess_data(img: Image.Image) -> Dict[str, List]:
    st = t()
    try:
        data = pytesseract.image_to_data(img, output_type=TessOutput.DICT, config="--psm 6", lang="eng")
        logger.debug("tesseract.image_to_data: words=%d time=%.4fs", len(data.get("text", [])), dt(st))
        return data
    except Exception as e:
        logger.error("Tesseract image_to_data failed: %s (%.4fs)", e, dt(st))
        return {"text": [], "left": [], "top": [], "width": [], "height": [], "conf": [], "block_num": [], "par_num": [], "line_num": []}

def _image_to_string(img: Image.Image, config: str = "--psm 6") -> str:
    st = t()
    try:
        txt = pytesseract.image_to_string(img, config=config, lang="eng") or ""
        logger.debug("tesseract.image_to_string: chars=%d time=%.4fs", len(txt), dt(st))
        return txt
    except Exception as e:
        logger.error("tesseract.image_to_string failed: %s (%.4fs)", e, dt(st))
        return ""

def _word_boxes_from_data(data: Dict[str, List]) -> List[Dict[str, Any]]:
    st = t()
    words = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        try:
            left = int(data["left"][i]); top = int(data["top"][i])
            w = int(data["width"][i]); h = int(data["height"][i])
        except Exception:
            continue
        try:
            conf = float(data.get("conf", [])[i])
        except Exception:
            conf = 0.0
        words.append({
            "text": txt,
            "left": left, "top": top, "right": left + w, "bottom": top + h,
            "w": w, "h": h, "conf": conf
        })
    logger.debug("word_boxes_from_data: words=%d time=%.4fs", len(words), dt(st))
    return words

def _sort_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort words for natural reading order (left-to-right, top-to-bottom).
    Group words into horizontal bands (within ~20px vertical tolerance), 
    then sort each band left-to-right.
    """
    st = t()
    if not words:
        return []
    
    # First sort by top to identify rows
    by_top = sorted(words, key=lambda w: w["top"])
    
    # Group into rows (words within 20px vertically are considered same row)
    rows = []
    current_row = [by_top[0]]
    row_top = by_top[0]["top"]
    
    for w in by_top[1:]:
        if abs(w["top"] - row_top) <= 20:  # Same row
            current_row.append(w)
        else:  # New row
            # Sort current row left-to-right
            current_row.sort(key=lambda x: x["left"])
            rows.extend(current_row)
            current_row = [w]
            row_top = w["top"]
    
    # Don't forget last row
    current_row.sort(key=lambda x: x["left"])
    rows.extend(current_row)
    
    logger.debug("sort_words: words=%d time=%.4fs", len(rows), dt(st))
    return rows

# -------------------------------------------------------------
# Alignment correction using OpenCV (deskew based on text angle)
# -------------------------------------------------------------
def _detect_and_correct_alignment(img: Image.Image, debug_save_dir: Optional[str] = None, page_idx: Optional[int] = None) -> Image.Image:
    """
    Detects and corrects skew or misalignment using OpenCV.
    Works well for slightly rotated text boxes (±10°).
    """
    if not _HAS_CV2:
        return img

    st = t()
    gray = np.array(img.convert("L"))
    h, w = gray.shape
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)

    # Use Hough transform to detect predominant line angles
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=max(80, int(min(h, w) * 0.15)))
    if lines is None or len(lines) == 0:
        logger.debug("Alignment: no Hough lines detected (%.4fs)", dt(st))
        return img

    # Convert angles from radians to degrees (normalize around 0)
    angles = []
    for rho_theta in lines[:200]:
        rho, theta = rho_theta[0]
        ang = (theta * 180 / np.pi) - 90
        # keep near-horizontal only
        if -45 < ang < 45:
            angles.append(ang)
    if not angles:
        return img

    median_angle = float(np.median(angles))
    logger.info("Detected skew angle: %.2f°", median_angle)

    # Rotate back if necessary
    if abs(median_angle) < 0.5:
        logger.debug("Alignment: image already aligned (%.4fs)", dt(st))
        return img

    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    aligned = Image.fromarray(rotated).convert("RGB")

    if debug_save_dir:
        _save_crop(aligned, prefix="crop_aligned", page_idx=page_idx, crop_dir=debug_save_dir)

    logger.info("Alignment corrected by %.2f° (%.4fs)", median_angle, dt(st))
    return aligned

# -------------------------------------------------------------
# Reorder and join jumbled/split words using image geometry
# -------------------------------------------------------------
def _reorder_and_join_words_on_image(crop_img: Image.Image, harvested_lines: List[str]) -> List[str]:
    """
    Attempt to reorder/join words based on actual OCR word boxes on the crop image.
    Strategy:
      1. Use pytesseract.image_to_data to get per-word bounding boxes for the crop.
      2. Group those boxes into rows (by top coordinate buckets).
      3. For each row (sorted by top -> left) join words with single spaces.
      4. Post-process adjacent word pairs: if horizontal gap between boxes is very small
         relative to average character width (or if boxes are overlapping), merge them.
      5. Return reconstructed rows (preferred) or fallback to harvested_lines.
    """
    st = t()
    try:
        data = _image_to_tess_data(crop_img)
        boxes = _word_boxes_from_data(data)
        if not boxes:
            logger.debug("_reorder_and_join_words_on_image: no boxes (%.4fs)", dt(st))
            return harvested_lines
        # Group into rows by top bucket
        rows: Dict[int, List[Dict[str, Any]]] = {}
        for b in boxes:
            bucket = int(b["top"] // 8)
            rows.setdefault(bucket, []).append(b)

        reconstructed = []
        # compute average char width approx using word widths / len(text)
        avg_char_w = None
        char_widths = []
        for b in boxes:
            if b["text"]:
                char_widths.append(b["w"] / max(1, len(b["text"])))
        if char_widths:
            avg_char_w = float(np.median(char_widths))
        else:
            avg_char_w = 6.0

        for k in sorted(rows.keys()):
            row = sorted(rows[k], key=lambda r: r["left"])
            # Join words but possibly merge adjacent boxes if gap tiny
            parts = []
            for i, w in enumerate(row):
                txt = w["text"].strip()
                if i == 0:
                    parts.append({"txt": txt, "left": w["left"], "right": w["right"]})
                    continue
                prev = parts[-1]
                gap = w["left"] - prev["right"]
                # threshold based on avg_char_w
                gap_thresh = max(1.0, avg_char_w * 0.4)
                if gap <= gap_thresh:
                    prev["txt"] = prev["txt"] + w["text"]
                    prev["right"] = w["right"]
                else:
                    parts.append({"txt": w["text"], "left": w["left"], "right": w["right"]})
            # convert parts to string
            row_str = " ".join(p["txt"] for p in parts)
            reconstructed.append(row_str.strip())

        reconstructed = [ _fix_common_ocr(r) for r in reconstructed if r and not _is_noise_line(r) ]

        if reconstructed:
            logger.debug("_reorder_and_join_words_on_image: reconstructed rows=%d (%.4fs)", len(reconstructed), dt(st))
            return _dedupe_lines(reconstructed)

    except Exception as e:
        logger.debug("_reorder_and_join_words_on_image: exception: %s (%.4fs)", e, dt(st))
        return harvested_lines

    logger.debug("_reorder_and_join_words_on_image: fallback to harvested (%.4fs)", dt(st))
    return harvested_lines

# -------------------------------------------------------------
# New: merge adjacent tokens if image OCR suggests they're a single word
# -------------------------------------------------------------
def _normalize_for_compare(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (s or "").lower())

def _crop_bbox_safe(img: Image.Image, bbox: Tuple[int,int,int,int], pad: int = 6) -> Image.Image:
    w,h = img.size
    x1,y1,x2,y2 = bbox
    x1 = max(0, x1 - pad); y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad); y2 = min(h, y2 + pad)
    return img.crop((x1,y1,x2,y2))

def _find_matching_box_for_token(token_norm: str, boxes: List[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    # best-effort: find a box whose normalized text contains token_norm or vice versa
    for b in boxes:
        if not b.get("text"):
            continue
        if token_norm in _normalize_for_compare(b["text"]) or _normalize_for_compare(b["text"]) in token_norm:
            return b
    # fallback: none
    return None

def _merge_adjacent_tokens_using_image(crop_img: Image.Image, lines: List[str], crop_save_dir: Optional[str] = None) -> List[str]:
    """
    For each line, inspect adjacent token pairs and, for suspicious pairs (short tokens,
    punctuation breaks), try to verify by cropping the image region for the two tokens,
    OCR-ing that region and comparing letter-wise similarity between:
      - region OCR (normalized)
      - concatenated tokens (normalized)
    If similarity >= dynamic threshold => merge tokens (no space).
    """
    st = t()
    out_lines = []
    try:
        data = _image_to_tess_data(crop_img)
        boxes = _word_boxes_from_data(data)
        if not boxes:
            logger.debug("_merge_adjacent_tokens_using_image: no boxes, skipping (%.4fs)", dt(st))
            return lines
        boxes_sorted = sorted(boxes, key=lambda b: (b["top"], b["left"]))

        # compute avg char width
        char_widths = [b["w"]/max(1,len(b["text"])) for b in boxes if b["text"]]
        avg_char_w = float(np.median(char_widths)) if char_widths else 6.0
        logger.debug("merge: avg_char_w=%.2f boxes=%d", avg_char_w, len(boxes_sorted))

        for li, line in enumerate(lines):
            tokens = [tok for tok in re.split(r'\s+', line.strip()) if tok]
            if len(tokens) < 2:
                out_lines.append(line)
                continue

            i = 0
            merged_tokens = []
            while i < len(tokens):
                cur = tokens[i]
                # candidate with next token
                merged_this_pair = False
                if i+1 < len(tokens):
                    nxt = tokens[i+1]
                    # heuristics: short token or trailing comma or small gap tokens are suspicious
                    suspicious = False
                    if len(cur) <= MERGE_SHORT_TOKEN_MAX_LEN or len(nxt) <= MERGE_SHORT_TOKEN_MAX_LEN:
                        suspicious = True
                    if cur.endswith(',') or cur.endswith('-') or nxt.startswith(',') or (',' in cur and cur.endswith(',')):
                        suspicious = True

                    if suspicious:
                        cur_norm = _normalize_for_compare(cur)
                        nxt_norm = _normalize_for_compare(nxt)
                        norm_concat = _normalize_for_compare(cur.rstrip(' ,.-') + nxt.lstrip(' ,.-'))
                        # find boxes for cur and nxt
                        b_cur = _find_matching_box_for_token(cur_norm, boxes_sorted)
                        b_nxt = _find_matching_box_for_token(nxt_norm, boxes_sorted)

                        # fallback pair selection: nearest pair with increasing left
                        if (b_cur is None or b_nxt is None) and boxes_sorted:
                            candidate_pair = None
                            for bi in range(len(boxes_sorted)-1):
                                a = boxes_sorted[bi]; b = boxes_sorted[bi+1]
                                if a["text"] and b["text"]:
                                    # heuristic: their texts' first characters match cur/nxt first char
                                    if cur and a["text"][0].lower() == cur[0].lower() and nxt and b["text"][0].lower() == nxt[0].lower():
                                        candidate_pair = (a,b); break
                            if candidate_pair:
                                if b_cur is None: b_cur = candidate_pair[0]
                                if b_nxt is None: b_nxt = candidate_pair[1]

                        if b_cur and b_nxt:
                            # ensure order
                            left = min(b_cur["left"], b_nxt["left"])
                            right = max(b_cur["right"], b_nxt["right"])
                            top = min(b_cur["top"], b_nxt["top"])
                            bottom = max(b_cur["bottom"], b_nxt["bottom"])
                            gap = b_nxt["left"] - b_cur["right"]
                            gap_ratio = gap / max(1.0, avg_char_w)

                            # prefer merging if gap small OR tokens very short
                            consider_by_gap = gap_ratio <= MERGE_MAX_GAP_RATIO

                            if consider_by_gap or len(cur) <= MERGE_SHORT_TOKEN_MAX_LEN or len(nxt) <= MERGE_SHORT_TOKEN_MAX_LEN:
                                region = _crop_bbox_safe(crop_img, (left, top, right, bottom), pad=int(max(4, avg_char_w)))
                                # OCR the mini-region (try psm 6 then 7)
                                region_text = _image_to_string(region, config="--psm 6").strip()
                                if not region_text:
                                    region_text = _image_to_string(region, config="--psm 7").strip()
                                norm_region = _normalize_for_compare(region_text)
                                logger.debug("merge-check: line=%d pair=(%s|%s) region_text='%s' norm_region='%s'", li, cur, nxt, region_text[:80], norm_region[:80])

                                # dynamic threshold: lower for short candidates
                                dyn_threshold = MERGE_SIM_THRESHOLD
                                if len(norm_concat) <= 6:
                                    dyn_threshold = max(0.50, MERGE_SIM_THRESHOLD - 0.2)

                                sim = SequenceMatcher(None, norm_region, norm_concat).ratio() if norm_region and norm_concat else 0.0
                                contains = norm_concat and (norm_concat in norm_region)

                                if MERGE_DEBUG_SAVE and crop_save_dir:
                                    try:
                                        _save_crop(region.convert("RGB"), prefix=f"merge_debug_l{li}_i{i}", page_idx=None, crop_dir=crop_save_dir)
                                    except Exception:
                                        pass

                                logger.debug("merge-eval: dyn_th=%.2f sim=%.3f contains=%s gap_ratio=%.2f", dyn_threshold, sim, contains, gap_ratio)

                                if sim >= dyn_threshold or contains:
                                    # merge without space (strip punctuation between)
                                    newtok = (cur.rstrip(' ,.-') + nxt.lstrip(' ,.-'))
                                    newtok = re.sub(r'\s{2,}', ' ', newtok)
                                    merged_tokens.append(newtok)
                                    i += 2
                                    merged_this_pair = True
                                else:
                                    # extra fallback: if concatenation exactly equals region_text (looser)
                                    if norm_region and norm_concat and norm_region == norm_concat:
                                        newtok = (cur.rstrip(' ,.-') + nxt.lstrip(' ,.-'))
                                        merged_tokens.append(newtok)
                                        i += 2
                                        merged_this_pair = True

                if not merged_this_pair:
                    merged_tokens.append(cur)
                    i += 1

            joined_line = " ".join(merged_tokens).strip()
            out_lines.append(_fix_common_ocr(joined_line))

        logger.debug("_merge_adjacent_tokens_using_image: done lines_in=%d out=%d time=%.4fs", len(lines), len(out_lines), dt(st))
        return out_lines

    except Exception as e:
        logger.debug("_merge_adjacent_tokens_using_image: exception: %s (%.4fs)", e, dt(st))
        return lines

# -------------------------------------------------------------
# Header-based right crop & contour crop functions (existing)
# -------------------------------------------------------------
def _find_header_index(words: List[Dict[str, Any]], pattern: re.Pattern) -> Optional[int]:
    st = t()
    best_match = None
    best_score = -1
    
    # Get image width to determine left vs right side
    img_w = 0
    if words:
        img_w = max(w.get("right", 0) for w in words)
    
    logger.debug(f"find_header_index: Pattern={pattern.pattern[:120]}, img_w={img_w}, 50%% threshold={int(img_w * 0.50) if img_w else 0}")
    
    for idx, w in enumerate(words):
        word_text = w.get("text", "").lower()
        word_left = w.get("left", 0)
        word_top = w.get("top", 0)
        
        # Skip words on the left half - that's the Recipient column (use 50% threshold for stricter filtering)
        if img_w > 0 and word_left < (img_w * 0.50):
            continue
        
        # Build context for ALL words on right side (not just keywords)
        # This ensures we don't miss matches where keywords are in different words
        # Expand context window to 10 words before/after to capture full header
        start = max(0, idx - 10); end = min(len(words), idx + 12)
        ctx = " ".join(words[j]["text"] for j in range(start, end))
        
        # Skip noise patterns
        if re.search(r'Delivery\s*Challan', ctx, re.IGNORECASE):
            continue
        if re.search(r'Original\s*for\s*Consignee', ctx, re.IGNORECASE):
            continue
            
        # Must match the delivery address pattern
        match = pattern.search(ctx)
        if match:
            score = 0
            if 'Address' in ctx:
                score += 10
            if 'Name' in ctx:
                score += 5
            # Heavily prefer further right (past 55% is much better)
            if word_left > (img_w * 0.55):
                score += 30  # Strong bonus for clearly right-side position
            elif word_left > (img_w * 0.50):
                score += 10  # Smaller bonus for borderline position
            
            # CRITICAL: Prefer delivery headers that appear HIGHER on the page (lower top value)
            # This ensures we get the primary delivery address, not secondary ones
            word_top = w.get("top", 9999)
            if word_top < 800:  # Upper portion of invoice (typical delivery address location)
                score += 20
            
            if score > best_score:
                best_score = score
                best_match = idx
                logger.debug("New best match at idx=%d left=%d top=%d score=%d ctx='%s'", idx, word_left, word_top, score, ctx[:80])
    
    if best_match is not None:
        logger.debug("find_header_index: found idx=%d score=%d time=%.4fs", best_match, best_score, dt(st))
        return best_match
        
    logger.debug("find_header_index: not found time=%.4fs", dt(st))
    return None

def _header_based_right_crop(image: Image.Image) -> Optional[Tuple[int,int,int,int,Image.Image]]:
    st_all = t()
    data = _image_to_tess_data(image)
    words = _word_boxes_from_data(data)
    if not words:
        logger.debug("header_based_right_crop: no words (time=%.4fs)", dt(st_all))
        return None
    words = _sort_words(words)

    st_find = t()
    # Strategy: Try "Name & Address of Delivery" first, then fall back to "Recipient" on right side
    idx = _find_header_index(words, HDR_DELIVERY_RE)
    header_kind = "delivery"
    
    # Fallback: If no delivery header found, try recipient header (but ONLY on right side >50%)
    if idx is None:
        idx = _find_header_index(words, HDR_RECIPIENT_RE)
        if idx is not None:
            header_kind = "recipient"
            logger.debug("Using recipient header as delivery address (no delivery header found)")
    
    logger.debug("header_based_right_crop: header_search time=%.4fs", dt(st_find))

    if idx is None:
        logger.debug("header_based_right_crop: header not found (time=%.4fs)", dt(st_all))
        return None

    hw = words[idx]
    img_w, img_h = image.size

    # Verify the header is actually on the right side (should be past 50% due to _find_header_index filtering)
    if hw["left"] < (img_w * 0.48):
        logger.warning("Header found but position is too far left (left=%d, 48%%=%d). Rejecting.", 
                       hw["left"], int(img_w * 0.48))
        return None
    
    logger.debug("Header validated at left=%d (48%% threshold=%d)", hw["left"], int(img_w * 0.48))

    row_tol = max(6, hw["h"]//2)
    # Keep the matched word's left position - don't expand to other columns
    anchor_left = hw["left"]
    anchor_right = hw["right"]
    anchor_top = hw["top"]
    anchor_bottom = hw["bottom"]
    
    # Only expand right and vertically within the same row - NOT leftward
    for w in words:
        if abs(w["top"] - hw["top"]) <= row_tol:
            # Only expand right if the word is also on the right side (avoid pulling in Recipient column)
            if w["left"] >= anchor_left:
                anchor_right = max(anchor_right, w["right"])
                anchor_bottom = max(anchor_bottom, w["bottom"])

    header_h = max(12, hw["h"])
    try:
        median_h = int(np.median([w["h"] for w in words if w.get("h")]))
    except Exception:
        median_h = header_h

    expected_lines = 8  # Expected address lines (company, street, city, state, etc.)
    # Reduce top margin - don't need much space above the header
    top_margin = int(header_h * 0.5)
    # Tighter bottom margin - capture address lines but not terms/conditions below
    # Use more conservative multiplier to avoid capturing too much
    bottom_margin = max(int(median_h * expected_lines * 1.2), header_h * 6, 280)
    # Final balanced padding - captures "Name & " in most layouts while 48% minimum prevents Recipient column
    side_pad = max(250, int(img_w * 0.11))  # 11% padding (~275px) final balanced value

    # Always use actual header position with padding, but ensure we stay on right half
    # Use the anchor position with padding, but never go below 48% of page width
    x1_candidate = anchor_left - side_pad
    x1 = max(int(img_w * 0.48), x1_candidate)  # Ensure x1 is at least 48% of page width
    
    logger.debug("Crop calc: anchor_left=%d side_pad=%d x1_candidate=%d img_w=%d 48%%=%d => x1=%d", 
                 anchor_left, side_pad, x1_candidate, img_w, int(img_w * 0.48), x1)

    x2 = min(img_w, img_w - int(img_w * 0.02))
    y1 = max(0, anchor_top - top_margin)
    y2 = min(img_h, anchor_bottom + bottom_margin)
    logger.debug("header_based_right_crop: box_compute time=%.4fs", dt(st_all))

    if x2 - x1 < 120 or y2 - y1 < 80:
        logger.debug("header_based_right_crop: invalid crop box (w=%d h=%d) time=%.4fs", x2-x1, y2-y1, dt(st_all))
        return None

    crop = image.crop((x1, y1, x2, y2))
    logger.info("Header-based RIGHT crop: x1=%d y1=%d x2=%d y2=%d header=%s (%.2fs)", x1, y1, x2, y2, header_kind, dt(st_all))
    return (int(x1), int(y1), int(x2), int(y2), crop)

def _contour_right_crop(image: Image.Image) -> Optional[Tuple[int,int,int,int,Image.Image]]:
    if not _HAS_CV2:
        return None
    st_all = t()
    arr = np.array(image.convert("L"))
    h_img, w_img = arr.shape
    try:
        blur = cv2.GaussianBlur(arr, (5,5), 0)
        th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 10)
    except Exception:
        _, th = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25,5))
    closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    # IMPORTANT: Only consider contours on the right half of the page (delivery column, not recipient)
    right_threshold = w_img * 0.45  # Must be past 45% to be considered right-side
    
    if contours:
        for cnt in contours:
            x,y,w,h = cv2.boundingRect(cnt)
            area = w*h
            # Skip small contours
            if area < (w_img*h_img)*0.0008:
                continue
            # CRITICAL: Only accept contours that start on the right side
            if x > right_threshold:
                candidates.append((area, x,y,w,h))
                logger.debug("Contour candidate: x=%d y=%d w=%d h=%d area=%d (right-side)", x, y, w, h, area)
            else:
                logger.debug("Contour rejected (too far left): x=%d threshold=%d", x, int(right_threshold))
                
        # If no right-side contours found with size filter, try larger contours only
        if not candidates:
            for cnt in contours:
                x,y,w,h = cv2.boundingRect(cnt)
                area = w*h
                # Still enforce right-side constraint even for large contours
                if area > (w_img*h_img)*0.005 and x > right_threshold:
                    candidates.append((area, x,y,w,h))
                    logger.debug("Contour candidate (large): x=%d y=%d w=%d h=%d area=%d", x, y, w, h, area)

    if not candidates:
        logger.debug("contour_right_crop: no candidates on right side (threshold=%.0f) time=%.4fs", right_threshold, dt(st_all))
        return None

    candidates.sort(key=lambda t_: t_[0], reverse=True)
    _, x,y,w,h = candidates[0]
    
    # Ensure the crop stays on the right half even after padding
    pad_x = min(80, int(w*0.06)); pad_y = min(80, int(h*0.06))
    x1 = max(int(w_img * 0.48), x-pad_x)  # Never go below 48% of page width
    y1 = max(0, y-pad_y)
    x2 = min(w_img, x+w+pad_x)
    y2 = min(h_img, y+h+pad_y)
    
    logger.debug("Contour crop: orig_x=%d pad_x=%d => x1=%d (48%% threshold=%d)", x, pad_x, x1, int(w_img * 0.48))
    
    crop = image.crop((x1,y1,x2,y2))
    logger.info("Contour-based RIGHT crop: x1=%d y1=%d x2=%d y2=%d (%.2fs)", x1, y1, x2, y2, dt(st_all))
    return (int(x1), int(y1), int(x2), int(y2), crop)

# -------------------------------------------------------------
# Preprocess crop for OCR (binarize/denoise)
# -------------------------------------------------------------
def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    st_all = t()
    if not _HAS_CV2:
        out = img.convert("L")
        logger.debug("preprocess_for_ocr: grayscale_only time=%.4fs", dt(st_all))
        return out
    arr = np.array(img.convert("L"))
    arr = cv2.fastNlMeansDenoising(arr, None, 7, 7, 21)
    try:
        th = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10)
    except Exception:
        _, th = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,1))
    processed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
    out = Image.fromarray(processed).convert("L")
    logger.debug("preprocess_for_ocr: total time=%.4fs", dt(st_all))
    return out

# -------------------------------------------------------------
# Harvest lines from crop (strips headers from each line)
# -------------------------------------------------------------
def _harvest_lines(crop_img: Image.Image, aggressive: bool = False) -> List[str]:
    st_all = t()
    data = _image_to_tess_data(crop_img)
    words = _word_boxes_from_data(data)
    lines: List[str] = []
    if words:
        by_row: Dict[int, List[Dict[str, Any]]] = {}
        for w in words:
            bucket = (w["top"] // 8)
            by_row.setdefault(bucket, []).append(w)
        rows: List[str] = []
        for k in sorted(by_row.keys()):
            row_words = sorted(by_row[k], key=lambda x: x["left"])
            txt = " ".join([rw["text"] for rw in row_words]).strip()
            if txt:
                rows.append(txt)

        stop_hits = 0
        for r in rows:
            r0 = r
            r_stripped = _strip_header_fragments_keep_rest(r0)
            if not r_stripped:
                continue
            r_fix = _fix_common_ocr(r_stripped)
            if not r_fix:
                continue
            if _is_noise_line(r_fix):
                continue
            if STOP_TOKENS.search(r_fix):
                stop_hits += 1
                if aggressive and stop_hits >= 1:
                    break
                if stop_hits >= 2:
                    break
                else:
                    continue
            else:
                stop_hits = 0
            lines.append(r_fix)
            if len(lines) >= 14:
                break

    if not lines:
        raw = _image_to_string(crop_img, config="--psm 6")
        candidates = []
        for l in raw.splitlines():
            l0 = l.strip()
            if not l0:
                continue
            l1 = _strip_header_fragments_keep_rest(l0) or ""
            l2 = _fix_common_ocr(l1) or ""
            if not l2 or _is_noise_line(l2):
                continue
            candidates.append(l2)
        lines = _dedupe_lines(candidates)[:14]

    lines = _dedupe_lines(lines)
    logger.info("Harvest lines: n=%d (%.2fs)", len(lines), dt(st_all))
    return lines

# -------------------------------------------------------------
# Optional helper: find recipient code
# -------------------------------------------------------------
def _find_recipient_code_on_page(page_img: Image.Image) -> Optional[str]:
    st_all = t()
    data = _image_to_tess_data(page_img)
    words = _word_boxes_from_data(data)
    if not words:
        return None
    by_row = {}
    for w in words:
        bucket = (w["top"] // 8)
        by_row.setdefault(bucket, []).append(w)
    lines = []
    for k in sorted(by_row.keys()):
        row_words = sorted(by_row[k], key=lambda x: x["left"])
        txt = " ".join([rw["text"] for rw in row_words]).strip()
        if txt:
            lines.append(_fix_common_ocr(txt))

    for ln in lines:
        m = re.search(r'(Recipient\s*Code\s*[:\-]?\s*)([A-Z0-9\:\-\/\s]+)', ln, re.IGNORECASE)
        if m:
            out = _fix_common_ocr(m.group(0))
            logger.info("Recipient code found (%.2fs): %s", dt(st_all), out)
            return out
    return None

# -------------------------------------------------------------
# Public API: structured extractor (RIGHT-SIDE ONLY)
# -------------------------------------------------------------
def extract_delivery_address_struct(
    input_path: str,
    * ,
    prefer_dpi: int = 300,  # OPTIMIZED: Reduced from 600 to 300 for 4x faster rendering
    poppler_path: Optional[str] = None,
    verbose: bool = False,
    crop_save_dir: Optional[str] = None,
    # legacy alias param for older callers
    save_crops: Optional[str] = None
) -> Optional[Dict[str, Optional[Any]]]:
    """
    Main function to extract delivery address structure from an image or PDF.
    Accepts crop_save_dir plus legacy save_crops (both treated the same).
    """
    if verbose:
        logger.setLevel(logging.DEBUG)

    # accept legacy param
    if save_crops and not crop_save_dir:
        crop_save_dir = save_crops

    overall_start = t()
    pages: List[Image.Image] = []
    ext = (os.path.splitext(input_path)[1] or "").lower()

    # Render/open input
    st_render = t()
    if ext == ".pdf":
        if not _HAS_PDF2IMG:
            logger.error("pdf2image not installed; cannot render PDF")
            return None
        try:
            if platform.system() == "Windows" and poppler_path:
                pages = convert_from_path(input_path, dpi=prefer_dpi, poppler_path=poppler_path)
            else:
                pages = convert_from_path(input_path, dpi=prefer_dpi)
            logger.info("PDF render: pages=%d in %.2fs", len(pages), dt(st_render))
        except Exception as e:
            logger.error("PDF render failed in %.2fs: %s", dt(st_render), e)
            return None
    else:
        try:
            pages = [Image.open(input_path).convert("RGB")]
            logger.info("Image load in %.2fs", dt(st_render))
        except Exception as e:
            logger.error("Image load failed in %.2fs: %s", dt(st_render), e)
            return None

    # Process pages (stop after first successful extraction)
    for p_idx, page in enumerate(pages, start=1):
        page_start = t()
        logger.info("Processing page %d/%d (right-box extraction)", p_idx, len(pages))

        # Try header-based crop first
        crop_info = None
        try:
            crop_info = _header_based_right_crop(page)
        except Exception as e:
            logger.debug("Header-based crop error: %s", e)
        logger.info("Header-based crop phase: %.2fs", dt(page_start))

        # Contour fallback
        if crop_info is None:
            try:
                crop_info = _contour_right_crop(page)
            except Exception as e:
                logger.debug("Contour-based crop error: %s", e)
        logger.info("Contour-based crop phase: %.2fs", dt(page_start))

        # Fallback to right-half crop
        if crop_info is None:
            w,h = page.size
            x1,y1,x2,y2 = int(w*0.49), 0, w, h
            crop = page.crop((x1,y1,x2,y2))
            crop_info = (x1,y1,x2,y2,crop)
            logger.info("Using fallback right-half crop")

        x1,y1,x2,y2,crop = crop_info

        # Save raw crop for debugging (always save)
        try:
            crop_path = _save_crop(crop, prefix="crop_raw", page_idx=p_idx, crop_dir=crop_save_dir)
        except Exception:
            crop_path = None

        # Alignment correction + Preprocess
        try:
            aligned = _detect_and_correct_alignment(crop, debug_save_dir=crop_save_dir, page_idx=p_idx)
        except Exception as e:
            logger.debug("Alignment correction failed: %s", e)
            aligned = crop
        logger.info("Alignment correction phase: %.2fs", dt(page_start))

        try:
            proc = _preprocess_for_ocr(aligned)
        except Exception as e:
            logger.debug("Preprocess exception: %s", e)
            proc = aligned.convert("L")
        logger.info("Preprocess phase: %.2fs", dt(page_start))

        try:
            preproc_path = _save_crop(proc.convert("RGB"), prefix="crop_preproc", page_idx=p_idx, crop_dir=crop_save_dir)
        except Exception:
            preproc_path = None

        # Harvest lines (first pass, preprocessed)
        try:
            lines = _harvest_lines(proc, aggressive=False)
        except Exception as e:
            logger.debug("Harvest exception (preprocessed): %s", e)
            lines = []
        logger.info("Harvest(preprocessed) phase: %s lines", len(lines))

        if not lines:
            try:
                lines = _harvest_lines(crop, aggressive=True)
            except Exception as e:
                logger.debug("Harvest exception (raw): %s", e)
                lines = []
        logger.info("Harvest(raw) phase: %s lines", len(lines))

        if not lines:
            logger.info("No lines harvested from right crop on this page; page_time=%.2fs", dt(page_start))
            continue

        # Remove any remaining header-only lines and keep the name properly
        filtered = []
        for ln in lines:
            if not ln:
                continue
            ln2 = _strip_header_fragments_keep_rest(ln) or ln
            ln2 = _fix_common_ocr(ln2)
            if not ln2:
                continue
            if HDR_DELIVERY_RE.fullmatch(ln2) or HDR_RECIPIENT_RE.fullmatch(ln2):
                continue
            filtered.append(ln2)
        lines = _dedupe_lines(filtered)
        logger.info("Filter+dedupe phase: kept=%d", len(lines))

        if not lines:
            logger.info("After header removal, no useful lines remain; page_time=%.2fs", dt(page_start))
            continue

        # Reorder / Join step using image geometry to correct jumbled/split words
        try:
            cleaned_lines_image = _reorder_and_join_words_on_image(aligned if 'aligned' in locals() else crop, lines)
            if cleaned_lines_image and len(cleaned_lines_image) >= 1:
                lines = cleaned_lines_image
        except Exception as e:
            logger.debug("Reorder/join step failed: %s", e)
        logger.info("Image-based reorder phase complete")

        # NEW: Image-verified merge of adjacent tokens (fix "Kan, galam" -> "Kangalam")
        try:
            merged_lines = _merge_adjacent_tokens_using_image(aligned if 'aligned' in locals() else crop, lines, crop_save_dir=crop_save_dir)
            if merged_lines and len(merged_lines) >= 1:
                lines = merged_lines
            logger.info("Starting letter-wise merge verification...")
        except Exception as e:
            logger.debug("Merge adjacent tokens step failed: %s", e)
        logger.info("_merge_adjacent_tokens_using_image complete")

        # Optional recipient code scan on full page
       #recipient_code = _find_recipient_code_on_page(page)

        # Build final single-line and aggressively strip header fragments globally
        raw_joined = ', '.join(lines) if lines else None
        cleaned_global = _remove_header_fragments_globally(raw_joined)
        if cleaned_global:
            cleaned = _fix_common_ocr(cleaned_global)
        else:
            cleaned = _fix_common_ocr(_strip_header_fragments_keep_rest(raw_joined) or raw_joined)

        # --- AI formatting step (BLOCKING) ---
        ai_result = None
        try:
            if ai_client and hasattr(ai_client, "format_address"):
                logger.info("Calling AI to format the cleaned address (blocking)...")
                try:
                    # pass the raw_joined or cleaned as input to AI
                    input_for_ai = cleaned or raw_joined or ""
                    # you can pass an api_key param here if you want to override env var:
                    # ai_result = ai_client.format_address(input_for_ai, api_key="YOUR_KEY_HERE")
                    ai_result = ai_client.format_address(input_for_ai)
                    logger.info("AI returned: %s", ai_result)
                except Exception as e:
                    logger.exception("AI formatting failed: %s", e)
                    ai_result = None
            else:
                logger.info("AI client not available or missing format_address(); skipping AI formatting.")
        except Exception as e:
            logger.exception("Unexpected error when calling AI: %s", e)
            ai_result = None

        if ai_result:
            final_cleaned = ai_result
        else:
            logger.info("AI returned empty result; keeping OCR cleaned value.")
            final_cleaned = cleaned

        # Apply aggressive header word cleaning (remove 'name', 'of', '&', 'delivery', etc.)
        final_cleaned = _clean_delivery_header_words(final_cleaned)

        page_time = dt(page_start)
        total_time = dt(overall_start)
        logger.info("Page %d complete: page_time=%.2fs total_elapsed=%.2fs", p_idx, page_time, total_time)

        result = {
            "right_box": final_cleaned,
            "right_lines": lines,
            #recipient_code": recipient_code,
            "crop_bbox": (int(x1), int(y1), int(x2), int(y2)),
            "crop_image_path": crop_path,
            "preproc_image_path": preproc_path,
            "timing": {
                "page_time_sec": round(page_time, 4),
                "overall_elapsed_sec": round(total_time, 4)
            }
        }
        logger.info("Extracted right_box with %d lines on page %d", len(lines), p_idx)
        logger.info("PASS-2 total so far: %.2fs", dt(overall_start))
        return result

    logger.warning("Right-side delivery box not found on any page (total=%.2fs)", dt(overall_start))
    return None

# -------------------------------------------------------------
# Backwards-compatible single-line API
# -------------------------------------------------------------
def extract_delivery_address_v2(
    input_path: str,
    * ,
    prefer_dpi: int = 300,  # OPTIMIZED: Reduced from 600 to 300 for 4x faster rendering
    poppler_path: Optional[str] = None,
    crop_save_dir: Optional[str] = None,
    save_crops: Optional[str] = None
) -> Optional[str]:
    out = extract_delivery_address_struct(input_path, prefer_dpi=prefer_dpi, poppler_path=poppler_path, crop_save_dir=crop_save_dir, save_crops=save_crops)
    if not out:
        return None
    return out.get("right_box")

# -------------------------------------------------------------
# CLI (for testing)
# -------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser(description="Delivery Address Extractor (RIGHT-SIDE only, Tesseract)")
    ap.add_argument("input", help="Path to PDF or image")
    ap.add_argument("--dpi", type=int, default=300)  # OPTIMIZED: Reduced from 600 to 300
    ap.add_argument("--poppler", dest="poppler_path")
    ap.add_argument("--verbose", action="store_true", help="Enable DEBUG logs (shows deep timing per step)")
    ap.add_argument("--crop-dir", dest="crop_dir", help="Directory to save crop debug images")
    ap.add_argument("--save-crops", dest="save_crops", help="Legacy alias for crop-dir")
    args = ap.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        res = extract_delivery_address_struct(args.input, prefer_dpi=args.dpi, poppler_path=args.poppler_path, verbose=args.verbose, crop_save_dir=args.crop_dir, save_crops=args.save_crops)
        if res:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            sys.exit(0)
        else:
            print("NULL")
            sys.exit(1)
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(2)
