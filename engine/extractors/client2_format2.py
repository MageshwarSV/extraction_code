# engine/extractors/client1_format3.py
# -------------------------------------------------------------
# Client 1 - Format 3 OCR Extractor  
# Extracts per-page: 
#   - Invoice pages: Branch, Invoice Date
#   - Consignment pages: GC Number
# Uses Tesseract for Branch/Date, EasyOCR for GC Numbers
# Returns page-by-page results
# -------------------------------------------------------------

import os
import sys
import re
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from difflib import SequenceMatcher

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Disable PIL decompression bomb limit
Image.MAX_IMAGE_PIXELS = None

# Import Format 3 extractors
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
from engine.extractors.deskew import deskew_and_enhance
from engine.extractors.gc_number_extractor import extract_gc_number_from_pdf_page

# -------------------------
# Logging
# -------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# Import for fuzzy matching
from difflib import SequenceMatcher

# EasyOCR for better OCR on distorted text
import easyocr
import numpy as np

# Initialize EasyOCR reader once (shared)
_easyocr_reader = None

def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easyocr_reader


# -------------------------
# Cleanup Debug Crops
# -------------------------
import shutil
import glob

def cleanup_debug_crops():
    """
    Delete all debug crop images after extraction completes.
    Called at the end of extraction to clean up temporary files.
    """
    base_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"
    
    # Directories to clean
    crop_dirs = [
        "actual_weight",
        "consignee",
        "delivery_address",
        "product_category",
        "consignee_crops",
        # Add any other crop directories here
    ]
    
    for crop_dir in crop_dirs:
        dir_path = os.path.join(base_dir, crop_dir)
        if os.path.exists(dir_path):
            # Delete all .png files in the directory
            for png_file in glob.glob(os.path.join(dir_path, "*.png")):
                try:
                    os.remove(png_file)
                except Exception:
                    pass
    
    logger.info("[CLEANUP] Deleted debug crop images")


# -------------------------
# Consignee Extraction (Bend/Curve Robust)
# -------------------------

def clean_trailing_noise(text):
    """Strip noise and unwanted artifacts from the start and end of the extracted name."""
    if not text:
        return text
    text = text.strip()
    
    # Symbols to strip from start/end (including space combinations)
    # Symbols: !@#$%^&*()`~_+-={}[]:";'<>,.?|
    # Use regex to iteratively strip whitespace + symbols from ends
    
    # Pattern: one or more of (whitespace OR these symbols) at start
    text = re.sub(r'^[\s!@#$%^&*()`~_+\-={}[\]:";\'<>,.?|]+', '', text)
    # Pattern: one or more of (whitespace OR these symbols) at end
    text = re.sub(r'[\s!@#$%^&*()`~_+\-={}[\]:";\'<>,.?|]+$', '', text)
    
    # Handle cases like "COMPANY LIMITED x" or "COMPANY é" (trailing single char - ANY character)
    if len(text) > 3:
        text = re.sub(r'\s+.$', '', text).strip()  # Remove space + any single char at end
        
    return text.strip()

def get_header_points(image_cv):
    """Find multiple points along the 'Recipient / Consignee' header to detect curvature."""
    data = pytesseract.image_to_data(image_cv, config='--psm 6', output_type=pytesseract.Output.DICT)
    points = []
    
    for i in range(len(data['text'])):
        text = data['text'][i].lower().strip()
        if not text: continue
            
        if 'recip' in text or 'consign' in text:
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
        
    # Standardize to one line
    avg_y = np.median([p['y'] for p in points])
    line_points = [p for p in points if abs(p['y'] - avg_y) < 25]
    
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

def extract_consignee_format3(page_image, page_num=0, debug=False) -> str:
    """
    Extract Consignee name using Bend-Crop (piecewise deskewing).
    Isolates the first line after "Recipient / Consignee".
    """
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Search area: upper right quadrant
    search_y1, search_y2 = int(height * 0.15), int(height * 0.45)
    search_x1, search_x2 = int(width * 0.40), int(width * 0.98)
    search_area = img_cv[search_y1:search_y2, search_x1:search_x2]
    
    header_points = get_header_points(search_area)
    
    if header_points:
        hw = header_points[-1]['right'] - header_points[0]['left']
        hx_start = header_points[0]['left']
        
        # Remap a strip starting below the header
        # Header is at ~20px in the remapped strip, so text starts at ~45px
        straightened = piecewise_deskew(search_area, header_points, target_y=20, crop_height=125)
        
        # Precision crop coordinates relative to the remapped strip
        crop_y1, crop_y2 = 45, 110 # approx 65px height for one line
        crop_x1 = max(0, hx_start - int(hw * 0.15))
        crop_x2 = min(search_area.shape[1], header_points[-1]['right'] + int(hw * 3.5))
        
        precision_crop = straightened[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if precision_crop.size == 0:
            return ""
            
        if debug:
            debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\debug_f3"
            if not os.path.exists(debug_dir): os.makedirs(debug_dir)
            cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_consignee.png"), precision_crop)
            
        # OCR
        gray = cv2.cvtColor(precision_crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if lines:
            return clean_trailing_noise(lines[0])
            
    return ""

def is_india_line(text):
    """
    Check if a line is the "INDIA" stop marker.
    Handles OCR errors: lNDlA, 1NDIA, INDlA, INDIA etc.
    """
    text_clean = re.sub(r'[^A-Z0-9]', '', text.upper())
    # Direct fuzzy match
    ratio = SequenceMatcher(None, text_clean, "INDIA").ratio()
    if ratio > 0.7: return True
    
    # Common OCR variants
    variants = ["INDIA", "lNDIA", "INDlA", "lNDlA", "1NDIA", "INDI", "NDIA"]
    if any(v in text_clean for v in variants):
        return True
        
    return False

def clean_address_lines(lines):
    """Clean up the extracted address text."""
    final_lines = []
    
    # Skip line 0 (Company Name)
    address_content = lines[1:] 
    
    stop_found = False
    for line in address_content:
        # Check for stop marker
        if is_india_line(line):
            final_lines.append("INDIA") # Ensure clean INDIA is last line
            stop_found = True
            break
            
        # Clean line
        l = line.strip()
        # Strip specific trailing noise chars like ; | !
        l = re.sub(r'\s*[;|!\\/]+$', '', l).strip()
        
        if l:
            final_lines.append(l)
            
    # Join with comma and space for single line output, avoiding double commas
    result = ""
    for i, line in enumerate(final_lines):
        if i == 0:
            result = line
        else:
            prev = final_lines[i-1].strip()
            if prev.endswith(','):
                result += " " + line
            else:
                result += ", " + line
    return result

def extract_delivery_address_format3(page_image, page_num=0, debug=False) -> str:
    """Extract Delivery Address using Bend-Crop and INDIA stop logic."""
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Search area same as consignee
    search_y1, search_y2 = int(height * 0.15), int(height * 0.45)
    search_x1, search_x2 = int(width * 0.40), int(width * 0.98)
    search_area = img_cv[search_y1:search_y2, search_x1:search_x2]
    
    header_points = get_header_points(search_area)
    
    if header_points:
        hw = header_points[-1]['right'] - header_points[0]['left']
        hx_start = header_points[0]['left']
        
        # Determine deskew height - need deeper for address (e.g. 500px)
        straightened = piecewise_deskew(search_area, header_points, target_y=20, crop_height=500)
        
        # Crop coordinates
        crop_y1 = 45
        crop_y2 = 450 # Go deep enough to catch "INDIA"
        
        # X range - same as consignee
        crop_x1 = max(0, hx_start - int(hw * 0.05)) # Slightly tighter left
        crop_x2 = min(search_area.shape[1], header_points[-1]['right'] + int(hw * 1.0)) # Wide right
        
        raw_crop = straightened[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if debug:
            debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_address_integrated"
            if not os.path.exists(debug_dir): os.makedirs(debug_dir)
            cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_address_raw.png"), raw_crop)
        
        # OCR
        gray = cv2.cvtColor(raw_crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        text = pytesseract.image_to_string(thresh, config='--psm 6')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if lines:
            return clean_address_lines(lines)
            
    return ""


def robust_invoice_ocr(roi_image):
    """
    Try multiple preprocessing techniques to extract the 10-digit invoice number.
    Essential for Page 6 where standard OTSU might be failing.
    """
    gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
    
    # Scale up for better digit resolution
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    # List of preprocessing strategies
    strategies = [
        ("OTSU", lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
        ("ADAPTIVE", lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)),
        ("ERODE", lambda img: cv2.erode(cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], np.ones((2,2), np.uint8), iterations=1)),
        ("RAW", lambda img: img),
        ("FIXED_TH", lambda img: cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)[1]),
    ]
    
    for name, func in strategies:
        processed = func(gray)
        
        # Try different PSM modes
        # PSM 7: Treat the image as a single text line.
        # PSM 6: Assume a single uniform block of text.
        for psm in [7, 6]:
            config = f'--psm {psm} outputbase digits'
            text = pytesseract.image_to_string(processed, config=config)
            
            # Clean and validate
            text_clean = text.replace(" ", "").replace("\n", "").strip()
            
            # Strict 10 digit match
            match = re.search(r'\d{10}', text_clean)
            if match:
                return match.group(0)
                
    # If all strict checks fail, try loose digit extraction on the best looking image (OTSU)
    # and see if we have exactly 10 digits
    processed = strategies[0][1](gray)
    text = pytesseract.image_to_string(processed, config='--psm 6')
    digits = re.sub(r'\D', '', text)
    if len(digits) == 10:
        return digits
        
    return ""

def extract_invoice_number_format3(page_image, page_num=0, debug=False) -> str:
    """Extract 'Internal Number' (Invoice Number) using fuzzy anchors and Robust OCR."""
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Restrict search to top half
    search_h = int(height * 0.5)
    search_img = img_cv[0:search_h, :]
    
    # 1. Detect "Internal Number" anchor
    data = pytesseract.image_to_data(search_img, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    # Look for "Internal" and "Number" close to each other
    internal_indices = []
    number_indices = []
    
    for i, text in enumerate(data['text']):
        text = text.lower().strip()
        if not text: continue
        
        if fuzzy_match(text, "internal", 0.8):
            internal_indices.append(i)
        elif fuzzy_match(text, "number", 0.8) or fuzzy_match(text, "no", 0.9): 
            number_indices.append(i)
            
    # Find pairings
    best_pair = None
    min_dist = float('inf')
    
    for i_idx in internal_indices:
        for n_idx in number_indices:
            # Must be roughly same Y (same line)
            y_diff = abs(data['top'][i_idx] - data['top'][n_idx])
            # Must be close in X (Number follows Internal)
            x_diff = data['left'][n_idx] - (data['left'][i_idx] + data['width'][i_idx])
            
            if y_diff < 15 and 0 < x_diff < 100:
                dist = x_diff + y_diff
                if dist < min_dist:
                    min_dist = dist
                    best_pair = (i_idx, n_idx)
    
    if best_pair:
        i_idx, n_idx = best_pair
        # Anchor found!
        # Define ROI to the RIGHT of "Number"
        anchor_right = data['left'][n_idx] + data['width'][n_idx]
        anchor_top = min(data['top'][i_idx], data['top'][n_idx])
        anchor_bottom = max(data['top'][i_idx] + data['height'][i_idx], data['top'][n_idx] + data['height'][n_idx])
        
        # Buffer
        y_center = (anchor_top + anchor_bottom) // 2
        crop_y1 = max(0, y_center - 30) # Generous vertical
        crop_y2 = min(search_h, y_center + 40)
        crop_x1 = anchor_right + 5 # Start just after "Number"
        crop_x2 = min(width, crop_x1 + 400) # Assuming 10 digits fit in 400px
        
        roi = search_img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if debug:
            debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\invoice_number_integrated"
            if not os.path.exists(debug_dir): os.makedirs(debug_dir)
            cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_inv_raw.png"), roi)
        
        # Use Robust OCR
        return robust_invoice_ocr(roi)
             
    return ""



def fuzzy_match(text1: str, text2: str, threshold: float = 0.6) -> bool:
    """Check if two strings are similar (handles OCR errors)"""
    ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    return ratio >= threshold


def extract_destination(text: str) -> str:
    """
    Extract destination from 'Dispatch To <destination>' pattern.
    Handles multi-word destinations and OCR errors.
    
    Args:
        text: Full OCR text from invoice page
        
    Returns:
        Destination string or empty string if not found
    """
    # Find lines containing "Dispatch To"
    lines = text.split('\n')
    
    for line in lines:
        # Skip lines without "Dispatch To" pattern
        if not re.search(r'dispatch\s*to', line, re.IGNORECASE):
            continue
        
        # Extract destination from this line only
        # Pattern: "Dispatch To" followed by words until end of meaningful content
        match = re.search(r'Dispatch\s*To\s*[:\s]*([A-Za-z][A-Za-z\s\-]*)', line, re.IGNORECASE)
        if match:
            destination = match.group(1).strip()
            
            # Clean up: remove trailing noise
            stop_words = ['incoterms', 'for-door', 'delivery', 'shipment', 'dispatch', 
                          'from', 'invoice', 'date', 'no', 'number', 'consignee']
            words = destination.split()
            clean_words = []
            for w in words:
                if w.lower() in stop_words:
                    break
                if len(w) == 1 and w.lower() not in ['a']:
                    continue
                clean_words.append(w)
            
            destination = ' '.join(clean_words).strip()
            
            # Remove trailing single letters (OCR noise)
            destination = re.sub(r'\s+[a-z]$', '', destination, flags=re.IGNORECASE)
            
            if len(destination) >= 3:
                return destination
    
    # Fallback: Fuzzy matching for OCR errors
    words = text.split()
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^a-zA-Z0-9]', '', word)
        
        if len(clean_word) >= 5 and fuzzy_match(clean_word, "dispatch", 0.5):
            for j in range(i+1, min(i+4, len(words))):
                next_word = re.sub(r'[^a-zA-Z0-9]', '', words[j])
                if fuzzy_match(next_word, "to", 0.6) or next_word.lower() == "to":
                    dest_words = []
                    for k in range(j+1, min(j+5, len(words))):
                        w = words[k]
                        clean_w = re.sub(r'[^a-zA-Z\-]', '', w)
                        if not clean_w or len(clean_w) < 2:
                            break
                        if any(c.isdigit() for c in w):
                            break
                        if clean_w.lower() in ['dispatch', 'from', 'invoice', 'date', 'no', 
                                               'incoterms', 'for-door', 'delivery', 'shipment']:
                            break
                        dest_words.append(clean_w)
                    
                    if dest_words:
                        result = ' '.join(dest_words)
                        result = re.sub(r'\s+[a-z]$', '', result, flags=re.IGNORECASE)
                        return result
    
    return ""


def _normalize_vehicle_ocr(plate: str) -> str:
    """
    Normalize common OCR errors in vehicle plates - SAME AS client1_format1.py
    Indian vehicle format: STATE(2) + DISTRICT(1-2) + SERIES(1-3) + NUMBER(3-4)
    
    Position-based normalization:
    - State (0-1): 2 letters - no change needed
    - District (2-3): digits - normalize letters to digits (O→0, I→1, S→5, B→8)
    - Series (4-6): letters - normalize digits to letters (8→B, 0→D, 1→I, 5→S)
    - Number (last): digits - normalize letters to digits (O→0, I→1, S→5, B→8)
    """
    if not plate:
        return plate
    
    plate = plate.upper().replace(' ', '').replace('-', '')
    
    def normalize_to_digits(text):
        """Convert common letter OCR errors to digits"""
        return (text
                .replace('O', '0')
                .replace('o', '0')
                .replace('I', '1')
                .replace('l', '1')
                .replace('|', '1')
                .replace('S', '5')
                .replace('s', '5')
                .replace('B', '8')
                .replace('G', '6')
                .replace('g', '6')
                .replace('Z', '2')
                .replace('D', '0'))
    
    def normalize_to_letters(text):
        """Convert common digit OCR errors to letters"""
        return (text
                .replace('8', 'B')
                .replace('0', 'D')
                .replace('1', 'I')
                .replace('5', 'S'))
    
    # Common State Code Corrections (Tesseract often misreads A as R)
    if plate.startswith('RP') and len(plate) >= 4 and plate[2:4].isdigit():
        # RP39 -> AP39 (RP is not a valid Indian state code, likely AP misread)
        plate = 'AP' + plate[2:]
    elif plate.startswith('KP') and len(plate) >= 4 and plate[2:4].isdigit():
        plate = 'AP' + plate[2:]
    
    # Handle 10-character plates: XX NN LL NNNN (2+2+2+4)
    if len(plate) == 10:
        state = plate[0:2]
        district = plate[2:4]
        series = plate[4:6]
        number = plate[6:10]
        
        district_norm = normalize_to_digits(district)
        series_norm = normalize_to_letters(series)
        number_norm = normalize_to_digits(number)
        
        return f"{state}{district_norm}{series_norm}{number_norm}"
    
    # Handle 9-character plates: Could be XX N LL NNNN (2+1+2+4) or XX NN L NNNN (2+2+1+4)
    elif len(plate) == 9:
        state = plate[0:2]
        
        # Check if position 3 is a letter (then 2+1+2+4) or digit (then 2+2+1+4)
        if plate[2].isdigit() and plate[3].isdigit():
            # Format: XX NN L NNNN (2+2+1+4) - e.g., TN18K7553
            district = plate[2:4]
            series = plate[4:5]
            number = plate[5:9]
        else:
            # Format: XX N LL NNNN (2+1+2+4) - e.g., KA1AN0922
            district = plate[2:3]
            series = plate[3:5]
            number = plate[5:9]
        
        district_norm = normalize_to_digits(district)
        series_norm = normalize_to_letters(series)
        number_norm = normalize_to_digits(number)
        
        return f"{state}{district_norm}{series_norm}{number_norm}"
    
    # Handle 11-character plates: XX NN LLL NNNN (2+2+3+4)
    elif len(plate) == 11:
        state = plate[0:2]
        district = plate[2:4]
        series = plate[4:7]
        number = plate[7:11]
        
        district_norm = normalize_to_digits(district)
        series_norm = normalize_to_letters(series)
        number_norm = normalize_to_digits(number)
        
        return f"{state}{district_norm}{series_norm}{number_norm}"
    
    # For other lengths, try regex pattern matching
    match = re.match(r'^([A-Z]{2})([0-9OIlSsBG]{1,2})([A-Z0-9]{1,3})([0-9OIlSsBG]{3,4})$', plate)
    if match:
        state = match.group(1)
        district = match.group(2)
        series = match.group(3)
        number = match.group(4)
        
        district_norm = normalize_to_digits(district)
        series_norm = normalize_to_letters(series)
        number_norm = normalize_to_digits(number)
        
        return f"{state}{district_norm}{series_norm}{number_norm}"
    
    return plate


def extract_vehicle_easyocr(page_image) -> str:
    """
    Extract vehicle number using EasyOCR for better handling of distorted/tilted text.
    Falls back gracefully if EasyOCR fails (e.g., on servers without AVX support).
    
    Args:
        page_image: PIL Image of the invoice page
        
    Returns:
        Vehicle number string or empty string if not found
    """
    try:
        reader = _get_easyocr_reader()
        
        # Convert PIL to numpy
        img_np = np.array(page_image)
        
        # Use EasyOCR to read all text
        results = reader.readtext(img_np)
        
        # Look for vehicle pattern in EasyOCR results
        for i, detection in enumerate(results):
            bbox, text, conf = detection
            
            # Check if this text contains "Vehicle"
            if 'vehicle' in text.lower() or 'veh' in text.lower():
                # Look in this detection and next few for vehicle number
                for j in range(i, min(i + 3, len(results))):
                    _, nearby_text, nearby_conf = results[j]
                    
                    # Look for Indian vehicle number pattern
                    # Pattern: XX NN XX NNNN (e.g., AP39WA6987, TN28BK1910)
                    patterns = [
                        r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})',
                        r'([A-Z]{2}[0-9]{1,2}[A-Z0-9]{1,4}[0-9]{2,4})',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, nearby_text, re.IGNORECASE)
                        if match and nearby_conf > 0.3:
                            vehicle = match.group(1).replace(' ', '').upper()
                            
                            # Validate: 8-12 chars, starts with 2 letters
                            if 8 <= len(vehicle) <= 12:
                                normalized = _normalize_vehicle_ocr(vehicle)
                                if len(normalized) >= 2 and normalized[0:2].isalpha():
                                    logger.info(f"[Vehicle] EasyOCR found: {normalized}")
                                    return normalized
    except RuntimeError as e:
        # Handle "could not create a primitive" error on servers without AVX support
        error_msg = str(e).lower()
        if 'primitive' in error_msg or 'mkl' in error_msg or 'onednn' in error_msg:
            logger.warning(f"[Vehicle] EasyOCR skipped (CPU compatibility issue), will use Tesseract")
        else:
            logger.warning(f"[Vehicle] EasyOCR RuntimeError: {e}")
    except Exception as e:
        logger.warning(f"[Vehicle] EasyOCR failed: {e}")
    
    return ""


def extract_vehicle(text: str) -> str:
    """
    Extract vehicle number from invoice page.
    Looks for 'Vehicle No' label and extracts the Indian plate format after it.
    Handles OCR errors like v6hil6 → vehicle, 88 → 28, etc.
    
    Args:
        text: Full OCR text from invoice page
        
    Returns:
        Vehicle number string or empty string if not found
    """
    # Primary patterns: extract vehicle number AFTER 'Vehicle No' label
    # Indian format: XX NN XX NNNN (e.g., TN28BK1910)
    primary_patterns = [
        # "Vehicle No TN28BK1910" - capture after label
        r'Vehicle\s*No\.?\s*[:\-]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})',
        # "Vehicle No. : TN28BK1910" - with punctuation
        r'Vehicle\s*(?:No|Number)\.?\s*[:\-/]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})',
        # Flexible: allow some OCR errors in the number
        r'Vehicle\s*No\.?\s*[:\-]?\s*([A-Z0-9]{2}\s*[0-9]{1,2}\s*[A-Z0-9]{1,3}\s*[0-9]{3,4})',
        # Handle line where LR appears after vehicle
        r'Vehicle\s*No\.?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})\s+(?:LR|L\s*R)',
        # Handle OCR noise like /" or special chars before vehicle number
        r'Vehicle\s*No\.?\s*[/"\'\-:=\s]*([A-Za-z]{2}\s*[0-9]{1,2}\s*[A-Za-z]{1,3}\s*[0-9]{3,4})',
        # Very flexible: any punctuation before, mixed case, allow waGg type OCR errors
        r'Vehicle\s*No\b[^A-Za-z0-9]*([A-Za-z]{2}[0-9]{1,2}[A-Za-z0-9]{1,4}[0-9]{2,4})',
        # Super flexible: just capture 8-12 alphanumerics after 'Vehicle No' and any non-alnum chars
        r'Vehicle\s*No\b[^A-Za-z0-9]*([A-Za-z0-9]{8,12})',
    ]
    
    for pattern in primary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vehicle = match.group(1).replace(' ', '').upper()
            
            # Validate: should be 8-12 chars
            if 8 <= len(vehicle) <= 12:
                # Normalize OCR errors
                normalized = _normalize_vehicle_ocr(vehicle)
                
                # Validate normalized plate starts with 2 letters
                if len(normalized) >= 2 and normalized[0:2].isalpha():
                    return normalized
    
    # Fallback: Fuzzy match for "Vehicle" keyword with severe OCR errors
    lines = text.split('\n')
    for line in lines:
        # Find words similar to "vehicle"
        words = line.split()
        for i, word in enumerate(words):
            clean = re.sub(r'[^a-zA-Z0-9]', '', word)
            if len(clean) >= 5 and fuzzy_match(clean, "vehicle", 0.6):
                # Look for "No" nearby and then the vehicle plate
                rest_of_line = ' '.join(words[i:])
                for pattern in primary_patterns:
                    # Adjust pattern to work with partial line
                    simple_pattern = r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})'
                    match = re.search(simple_pattern, rest_of_line, re.IGNORECASE)
                    if match:
                        vehicle = match.group(1).replace(' ', '').upper()
                        if 8 <= len(vehicle) <= 12:
                            normalized = _normalize_vehicle_ocr(vehicle)
                            if len(normalized) >= 2 and normalized[0:2].isalpha():
                                return normalized
                break
    
    return ""


def extract_eway_bill_refined(text: str) -> str:
    """
    Extract 12-digit E-Way Bill number from OCR text.
    Handles label variations and noise.
    """
    # 1. Look for E-Way label with fuzzy variations
    label_patterns = [
        r'E-Way\s*No',
        r'E-Way\s*Bill\s*No',
        r'E-Way\s*No/Validity',
        r'E-WayNo',
        r'E\s*Way\s*Bill',
        r'E-Wway\s*No', # OCR error variation
        r'E-Way\s*Ne',   # OCR error variation
        r'Validity'
    ]
    
    # Combined regex for label + potential characters + 12 digits
    for pattern in label_patterns:
        regex = rf'({pattern})[^0-9\n]*(\d{{12}})'
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            eway_no = match.group(2)
            logger.info(f"[E-Way] Found with label '{match.group(1)}': {eway_no}")
            return eway_no

    # 2. Fallback: Search for any 12-digit number that matches E-Way bill format
    all_12_digits = re.findall(r'\b\d{12}\b', text)
    if all_12_digits:
        logger.info(f"[E-Way] Found 12-digit sequence as fallback: {all_12_digits[0]}")
        return all_12_digits[0]
    
    # 3. Last Fallback: Even if digits are broken or mixed with letters
    for pattern in label_patterns:
        match = re.search(rf'({pattern})(.{{1,20}})', text, re.IGNORECASE)
        if match:
            potential_num = match.group(2)
            # Normalize common OCR errors in digits
            normalized = (potential_num
                          .replace('O', '0')
                          .replace('o', '0')
                          .replace('I', '1')
                          .replace('l', '1')
                          .replace('S', '5')
                          .replace('s', '5')
                          .replace('B', '8')
                          .replace('G', '6'))
            digit_match = re.search(r'(\d{12})', normalized)
            if digit_match:
                logger.info(f"[E-Way] Found after normalization: {digit_match.group(1)}")
                return digit_match.group(1)
                
    return ""


def extract_consignor_refined(text: str) -> str:
    """
    Extract Consignor name with specific mapping rules:
    - JSW CEMENT LIMITED - NANDYAL -> JSW CEMENT LIMITED NANDYAL
    - JSW CEMENT LIMITED - SALEM -> JSW CEMENT LIMITED POTTANERI
    Supports fuzzy matching for bended/distorted text.
    """
    # Patterns to look for
    consignor_base = "JSW CEMENT LIMITED"
    
    # city patterns
    cities = {
        "SALEM": "POTTANERI",
        "NANDYAL": "NANDYAL"
    }

    lines = text.split('\n')
    for line in lines:
        line_upper = line.upper()
        
        # Look for JSW CEMENT LIMITED or JSWCL
        is_jsw = False
        if "JSW CEMENT LIMITED" in line_upper or "JSWCL" in line_upper:
            is_jsw = True
        else:
            # Fuzzy match base
            words = line_upper.split()
            for word in words:
                # SequenceMatcher ratio check for fuzzy matching
                if SequenceMatcher(None, word, "JSWCL").ratio() >= 0.7 or SequenceMatcher(None, word, "JSW").ratio() >= 0.8:
                    is_jsw = True
                    break
        
        if is_jsw:
            # Found JSW, now look for city
            for city_key, city_map in cities.items():
                if city_key in line_upper or SequenceMatcher(None, line_upper, city_key).ratio() >= 0.5:
                    logger.info(f"[Consignor] Found {city_key} in line: {line.strip()}")
                    return f"JSW CEMENT LTD-{city_map}"
            continue
            
    # Fallback: search whole text for the city near JSW
    for city_key, city_map in cities.items():
        if city_key in text.upper():
            logger.info(f"[Consignor] Found {city_key} via global search")
            return f"JSW CEMENT LTD-{city_map}"
            
    return "JSW CEMENT LTD"


def extract_actual_weight_format3(page_image, page_num=0, debug=False) -> str:
    """
    Extract 'Actual Weight (Qty in MT)' from Format 3 invoices.
    Uses Robust Anchors (Rate/Packing/Amount) + Adaptive Expansion Loop + EasyOCR.
    """
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Debug directory
    debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\actual_weight_integrated"
    if debug and not os.path.exists(debug_dir): 
        os.makedirs(debug_dir)
    
    # Crop focused region (30-65% vertical)
    region_y1 = int(height * 0.30)
    region_y2 = int(height * 0.65)
    region = img_cv[region_y1:region_y2, :]
    
    if debug:
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_region.png"), region)

    # Try different PSM modes on the REGION
    psm_modes = [6, 4, 3]
    
    for psm in psm_modes:
        data = pytesseract.image_to_data(region, config=f'--psm {psm}', output_type=pytesseract.Output.DICT)
        
        anchor = None
        anchor_type = None # 'rate' (right) or 'packing' (left)
        
        for i, text in enumerate(data['text']):
            t = text.strip().lower()
            if not t: continue
            
            # Anchor 1: "Rate" (or "Rate Per MT") -> Qty is LEFT
            if ('rate' in t) or ('per' in t and 'mt' in t) or ('er' in t and 'mt' in t):
                anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                anchor_type = 'rate'
                break
                
            # Anchor 2: "Packing" (or "Packing Type") -> Qty is RIGHT
            if 'packing' in t or 'cking' in t:
                anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                anchor_type = 'packing'
                break

            # Anchor 3: "Amount" (far right) -> Qty is 2 columns LEFT
            if 'amount' in t and ('net' not in t):
                 anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                 anchor_type = 'amount'
                 break

            # Anchor 4: "HSN" 
            if 'hsn' in t:
                 anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                 anchor_type = 'hsn'
                 
        if anchor:
            # Calculate Qty Box based on Anchor Type (Rel to REGION)
            crop_y1 = anchor['top'] + anchor['height'] + 5
            crop_y2 = min(region.shape[0], crop_y1 + 100) # Look below header
            
            if anchor_type == 'rate':
                crop_x2 = max(0, anchor['left'] - 5) 
                crop_x1 = max(0, anchor['left'] - 230)
                
            elif anchor_type == 'packing':
                # Reduced width to 150 to avoid Rate column
                crop_x1 = anchor['left'] + anchor['width'] + 5
                crop_x2 = min(region.shape[1], crop_x1 + 150)
                
            elif anchor_type == 'amount':
                crop_x2 = max(0, anchor['left'] - 350) 
                crop_x1 = max(0, anchor['left'] - 750)
                
            elif anchor_type == 'hsn':
                 crop_x1 = max(0, anchor['left'] + 400) 
                 crop_x2 = min(region.shape[1], crop_x1 + 400)

            # Define initial ROI
            # roi = region[crop_y1:crop_y2, crop_x1:crop_x2] # Not used directly, used in try_ocr

            # Helper to remove vertical lines (grid lines)
            def remove_vertical_lines(img_chk):
                try:
                    gray = cv2.cvtColor(img_chk, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 2)
                    # Vertical kernel to detect lines
                    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
                    detected_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
                    # Dilate to cover edges
                    detected_lines = cv2.dilate(detected_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
                    # Paint white
                    res = img_chk.copy()
                    res[detected_lines > 0] = [255, 255, 255]
                    return res
                except:
                    return img_chk

            # Helper to run OCR on a specific crop padding
            def try_ocr(p_left, p_right):
                c_x1 = max(0, crop_x1 - p_left)
                c_x2 = min(region.shape[1], crop_x2 + p_right)
                if c_x2 <= c_x1: return None
                
                roi_curr = region[crop_y1:crop_y2, c_x1:c_x2]
                
                # Preprocess: Remove Grid Lines
                roi_curr = remove_vertical_lines(roi_curr)
                
                roi_padded_curr = cv2.copyMakeBorder(roi_curr, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[255, 255, 255])
                
                if debug:
                    cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_crop_L{p_left}_R{p_right}.png"), roi_padded_curr)

                # EasyOCR
                try:
                     reader_obj = _get_easyocr_reader()
                     results = reader_obj.readtext(roi_padded_curr)
                     for (bbox, text, prob) in results:
                        txt = text.replace(" ", "").replace(",", ".")
                        m = re.search(r'(\d*\.?\d+)', txt) # Capture broader pattern
                        if m: return m.group(1)
                except: pass
                
                # Tesseract Fallback
                try:
                    gray = cv2.cvtColor(roi_padded_curr, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    txt = pytesseract.image_to_string(thresh, config='--psm 7').strip()
                    m = re.search(r'(\d*\.?\d+)', txt.replace(" ", ""))
                    if m: return m.group(1)
                except: pass
                return None

            # Loop Logic
            current_left = 0
            current_right = 0
            best_weight = None
            
            # Max iterations (50 -> 100px)
            for i in range(50): 
                val = try_ocr(current_left, current_right)
                
                if val:
                    # HEURISTIC: Fix trailing '1' (grid line artifact)
                    if val.endswith('1') and "." in val and len(val.split(".")[1]) == 3:
                        val = val[:-1] + '0'

                    # Check for perfect match (3 decimals)
                    if re.match(r'^\d+\.\d{3}$', val):
                        return val # Success!
                    
                    # Update best
                    if not best_weight or len(val) > len(best_weight):
                        best_weight = val
                    
                    # Decide Direction
                    if re.search(r'\.\d{0,2}$', val): # Missing Tail
                        current_right += 2 
                        continue

                    if val.startswith('.'): # Missing Head
                        current_left += 2 
                        continue
                        
                    if not re.search(r'\.\d{3}$', val):
                         current_right += 2
                    else:
                         if current_left == 0 and len(val) < 6: # Heuristic
                              current_left += 5
                         else:
                              break # Assume done
                else:
                    # No value found. Expand both?
                    current_left += 2
                    current_right += 2
            
            # Strict match not found, try next anchor (don't return best_weight yet)

    return ""


def extract_eway_date_format3(page_image, page_num=0, debug=False) -> str:
    """
    Extract E-Way Validity Date from Format 3 invoices.
    Uses Tesseract OCR with regex patterns that handle OCR variations (. / :)
    """
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Full page OCR
    text = pytesseract.image_to_string(gray, config='--psm 6')
    
    # Patterns with colon support (OCR sometimes reads . as :)
    patterns = [
        r'E-?Way.*?Validity.*?(\d{12})\s*[-]\s*(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})',
        r'(\d{12})\s*[-]\s*(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})',
        r'Validity.*?(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})',
        r'E-?Way.*?No.*?(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})'
    ]
    
    lines = text.split('\n')
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    date_val = match.group(2)
                    if re.match(r'\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4}', date_val):
                        # Normalize to dots
                        date_val = date_val.replace(':', '.').replace('/', '.')
                        return date_val
                elif len(match.groups()) == 1:
                    val = match.group(1)
                    if re.match(r'\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4}', val):
                        val = val.replace(':', '.').replace('/', '.')
                        return val
    return ""


def extract_pan_gst_format3(page_image, page_num=0, debug=False):
    """
    Extract PAN NO and GST No from Format 3 invoices.
    Returns: (pan_no, gst_no)
    """
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Full page OCR
    text = pytesseract.image_to_string(gray, config='--psm 6')
    
    pan_no = None
    gst_no = None
    
    # PAN NO Pattern: 10-character alphanumeric (5 letters + 4 digits + 1 letter)
    # Example: AABCJ6731B
    pan_patterns = [
        r'PAN\s*(?:NO\.?|Number)?[:\s]*([A-Z]{5}[0-9]{4}[A-Z])',
        r'PAN\s*(?:NO\.?)?[:\s]*([A-Z0-9]{10})',
    ]
    
    for pattern in pan_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).upper()
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', val):
                pan_no = val
                break
    
    # GST NO Pattern: 15-character (2 digits + PAN + 1 digit + Z + 1 alphanumeric)
    # Example: 33AABCJ6731B1Z3
    gst_patterns = [
        r'GST\s*(?:NO\.?|Number|IN)?[:\s]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z])',
        r'GSTIN[:\s]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z])',
        r'GST\s*(?:NO\.?)?[:\s]*([0-9A-Z]{15})',
    ]
    
    for pattern in gst_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).upper()
            if len(val) == 15 and val[:2].isdigit():
                gst_no = val
                break
    
    return pan_no, gst_no


def get_product_category(text_block):
    """
    Map extracted product description text to Category.
    """
    text_upper = text_block.upper()
    
    # 1. BOPP / LPP indicators
    if "LPP" in text_upper: return "BOPP BAG"
    if "L1PP" in text_upper: return "BOPP BAG"
    if "1PP" in text_upper: return "BOPP BAG"
    if "IPP" in text_upper: return "BOPP BAG"
    if "BOPP" in text_upper: return "BOPP BAG"
    if "LAMINATED" in text_upper: return "BOPP BAG"
    if "LOMINATED" in text_upper: return "BOPP BAG"
    if "IAMINATED" in text_upper: return "BOPP BAG"
    if "WATERGUARD" in text_upper: return "BOPP BAG"
    if "WG-BG" in text_upper: return "BOPP BAG"
    
    # 2. GGBS
    if "GGBS" in text_upper: return "GGBS"
    if "GG8S" in text_upper: return "GGBS"
    if "GGB5" in text_upper: return "GGBS"
    
    # 3. AD STAR
    if "AD STAR" in text_upper: return "AD STAR"
    if "ADSTAR" in text_upper: return "AD STAR"
    if "AD-STAR" in text_upper: return "AD STAR"
    
    return "UNKNOWN"


def extract_product_category_format3(page_image, page_num=0, debug=False):
    """
    Extract Product Category from Format 3 invoices.
    Uses header row detection and category mapping.
    """
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Product Name table is in MIDDLE of page (35-65% vertically)
    search_y1 = int(height * 0.35)
    search_y2 = int(height * 0.65)
    search_roi = img_cv[search_y1:search_y2, :]
    
    # OCR the region
    gray = cv2.cvtColor(search_roi, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray, config='--psm 6')
    
    # Map to category
    category = get_product_category(text)
    
    # FALLBACK: If UNKNOWN, search full page
    if category == "UNKNOWN":
        full_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        full_text = pytesseract.image_to_string(full_gray, config='--psm 6')
        category = get_product_category(full_text)
    
    return category


def extract_format3_data(pdf_path: str, dpi: int = 300) -> Dict[str, Any]:
    """
    Extract data from Format 3 PDF - page by page
    
    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for PDF conversion (default 200)
        
    Returns:
        Dictionary with page-by-page results:
        {
            "pages": [
                {"page": 1, "type": "CONSIGNMENT", "gc_number": "14549"},
                {"page": 2, "type": "INVOICE", "branch": "POTTANERI", "invoice_date": "12.12.2025"},
                ...
            ],
            "total_pages": 20,
            "invoice_pages": 11,
            "consignment_pages": 9,
            "extraction_timestamp": "2025-12-25 15:30:00",
            "status": "success",
            "error_message": None
        }
    """
    
    result = {
        "pages": [],
        "total_pages": 0,
        "invoice_pages": 0,
        "consignment_pages": 0,
        "extraction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "success",
        "error_message": None
    }
    
    try:
        logger.info(f"Processing Format 3 PDF: {pdf_path}")
        
        # Convert PDF to images
        pages = convert_from_path(pdf_path, dpi=dpi)
        result["total_pages"] = len(pages)
        logger.info(f"Converted {len(pages)} pages")
        
        # Process each page
        for page_num, page in enumerate(pages, 1):
            logger.info(f"[INFO] Processing page {page_num}/{len(pages)}")
            
            page_data = {
                "page": page_num,
                "type": None
            }
            
            # =============================================
            # STEP 1: TRY ALL 4 ROTATIONS TO DETECT CONSIGNMENT PAGE
            # Order: 90deg -> 0deg -> 180deg -> 270deg
            # Only if ALL rotations fail to find CONSIGNMENT, treat as INVOICE
            # =============================================
            
            consignment_rotations = [90, 0, 180, 270]  # 90deg is most common for consignment
            is_consignment = False
            consignment_rotation = None
            consignment_text = None
            
            for rotation_angle in consignment_rotations:
                logger.info(f"[CONSIGNMENT CHECK] Page {page_num}: Trying rotation {rotation_angle} deg")
                
                if rotation_angle == 0:
                    test_page = page
                else:
                    test_page = page.rotate(rotation_angle, expand=True)
                
                test_text = pytesseract.image_to_string(test_page, config='--psm 6')
                
                # Check for CONSIGNMENT NOTE indicators
                if 'CONSIGNMENT' in test_text.upper() and 'NOTE' in test_text.upper():
                    logger.info(f"[CONSIGNMENT FOUND] Page {page_num}: Detected CONSIGNMENT at rotation {rotation_angle} deg")
                    is_consignment = True
                    consignment_rotation = rotation_angle
                    consignment_text = test_text
                    break
            
            if is_consignment:
                # This is a CONSIGNMENT page
                page_data["type"] = "CONSIGNMENT"
                result["consignment_pages"] += 1
                
                # Extract GC number using EasyOCR at 300 DPI
                pages_300 = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
                page_300 = pages_300[0] if pages_300 else page
                
                # First try at the rotation where CONSIGNMENT was found
                if consignment_rotation == 0:
                    page_300_rotated = page_300
                else:
                    page_300_rotated = page_300.rotate(consignment_rotation, expand=True)
                
                gc_number = extract_gc_number_from_pdf_page(page_300_rotated)
                
                # If GC not found at detected rotation, try other rotations
                if not gc_number:
                    other_rotations = [r for r in [90, 0, 180, 270] if r != consignment_rotation]
                    for fallback_rotation in other_rotations:
                        if fallback_rotation == 0:
                            test_page = page_300
                        else:
                            test_page = page_300.rotate(fallback_rotation, expand=True)
                        
                        gc_number = extract_gc_number_from_pdf_page(test_page)
                        if gc_number:
                            logger.info(f"[GC FOUND] Page {page_num}: GC found at fallback rotation {fallback_rotation} deg")
                            break
                
                page_data["gc_number"] = gc_number
                
                if gc_number:
                    logger.info(f"[INFO] Page {page_num}: CONSIGNMENT, GC: {gc_number}")
                else:
                    logger.warning(f"[WARNING] Page {page_num}: CONSIGNMENT, GC: NOT FOUND")
            else:
                # This is an INVOICE page - apply deskew and extract
                page_data["type"] = "INVOICE"
                result["invoice_pages"] += 1
                
                # =============================================
                # ROTATION FALLBACK LOGIC FOR INVOICE PAGES
                # Try rotations: 0deg (deskew) -> 180deg -> 270deg -> 90deg
                # Only return empty if ALL rotations fail
                # =============================================
                
                rotation_order = [0, 180, 270, 90]  # Rotation angles to try
                best_extraction = None
                best_score = 0
                
                for rotation_angle in rotation_order:
                    logger.info(f"[INFO] Page {page_num}: Trying rotation {rotation_angle} deg")
                    
                    # Apply rotation
                    if rotation_angle == 0:
                        # Try deskew for 0deg orientation
                        try:
                            page_rotated = deskew_and_enhance(page)
                        except Exception as e:
                            logger.warning(f"Deskew failed on page {page_num}: {e}")
                            page_rotated = page
                    else:
                        # Apply rotation
                        page_rotated = page.rotate(rotation_angle, expand=True)
                        # Also try deskew after rotation
                        try:
                            page_rotated = deskew_and_enhance(page_rotated)
                        except Exception as e:
                            logger.warning(f"Deskew after rotation {rotation_angle} deg failed: {e}")
                    
                    # Run OCR - Using PSM 6 which is more stable for line-based extraction
                    text = pytesseract.image_to_string(page_rotated, config='--psm 6')
                    
                    # Extract critical fields for scoring
                    branch_test = extract_branch_refined(text)
                    invoice_date_test = extract_invoice_date_format3(text)
                    
                    # Calculate extraction score (critical fields)
                    current_score = 0
                    if branch_test:
                        current_score += 2  # Branch is important
                    if invoice_date_test:
                        current_score += 2  # Date is important
                    
                    # Also check for other indicators
                    if 'INVOICE' in text.upper():
                        current_score += 1
                    if 'DISPATCH' in text.upper():
                        current_score += 1
                    if 'VEHICLE' in text.upper():
                        current_score += 1
                    
                    logger.info(f"[INFO] Rotation {rotation_angle} deg: Branch={branch_test}, Date={invoice_date_test}, Score={current_score}")
                    
                    # If we found good extraction, use it
                    if branch_test and invoice_date_test:
                        # Perfect match - use this rotation
                        logger.info(f"[SUCCESS] Found valid extraction at rotation {rotation_angle} deg")
                        best_extraction = {
                            'page': page_rotated,
                            'text': text,
                            'branch': branch_test,
                            'invoice_date': invoice_date_test,
                            'rotation': rotation_angle
                        }
                        best_score = current_score
                        break  # Found good extraction, stop trying
                    
                    # Track best so far
                    if current_score > best_score:
                        best_score = current_score
                        best_extraction = {
                            'page': page_rotated,
                            'text': text,
                            'branch': branch_test,
                            'invoice_date': invoice_date_test,
                            'rotation': rotation_angle
                        }
                
                # Use best extraction found (or last attempt if all failed)
                if best_extraction:
                    page_corrected = best_extraction['page']
                    text = best_extraction['text']
                    branch = best_extraction['branch']
                    invoice_date = best_extraction['invoice_date']
                    logger.info(f"[INFO] Using rotation {best_extraction['rotation']} deg with score {best_score}")
                else:
                    # Fallback to original page with deskew
                    try:
                        page_corrected = deskew_and_enhance(page)
                    except Exception:
                        page_corrected = page
                    text = pytesseract.image_to_string(page_corrected, config='--psm 6')
                    branch = extract_branch_refined(text)
                    invoice_date = extract_invoice_date_format3(text)
                
                # Extract remaining fields using the best rotation
                destination = extract_destination(text)
                vehicle_no = extract_vehicle(text)
                eway_bill_no = extract_eway_bill_refined(text)
                consignor = extract_consignor_refined(text)
                # Pass the rotated page to consignee extractor (it has its own deskewing)
                consignee = extract_consignee_format3(page_corrected, page_num=page_num, debug=True)
                # Extract Delivery Address (Bend-Crop + Stop-at-INDIA)
                delivery_address = extract_delivery_address_format3(page_corrected, page_num=page_num, debug=True)
                # Extract Invoice Number (Internal Number)
                invoice_number = extract_invoice_number_format3(page_corrected, page_num=page_num, debug=True)
                # Extract Actual Weight
                actual_weight = extract_actual_weight_format3(page_corrected, page_num=page_num, debug=True)
                # Extract E-Way Validity Date
                eway_date = extract_eway_date_format3(page_corrected, page_num=page_num, debug=True)
                # Extract PAN NO and GST No
                pan_no, gst_no = extract_pan_gst_format3(page_corrected, page_num=page_num, debug=True)
                # Extract Product Category
                product_category = extract_product_category_format3(page_corrected, page_num=page_num, debug=True)
                
                page_data["branch"] = branch
                page_data["invoice_date"] = invoice_date
                page_data["invoice_number"] = invoice_number
                page_data["destination"] = destination
                page_data["vehicle_no"] = vehicle_no
                page_data["eway_bill_no"] = eway_bill_no
                page_data["eway_date"] = eway_date
                page_data["pan_no"] = pan_no
                page_data["gst_no"] = gst_no
                page_data["product_category"] = product_category
                page_data["consignor"] = consignor
                page_data["consignee"] = consignee
                page_data["delivery_address"] = delivery_address
                page_data["actual_weight"] = actual_weight
                
                if branch or invoice_date or destination or vehicle_no or eway_bill_no or consignor or consignee:
                    logger.info(f"Page {page_num}: INVOICE, Branch: {branch}, Date: {invoice_date}, InvNo: {invoice_number}, EWayDate: {eway_date}")
                else:
                    logger.info(f"Page {page_num}: INVOICE (no data found)")
            
            result["pages"].append(page_data)
            
    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        logger.error(f"Extraction failed: {e}", exc_info=True)
    
    # Cleanup debug crops after extraction
    cleanup_debug_crops()
    
    return result


def extract_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Main entry point for Format 3 extraction
    Alias for extract_format3_data() for consistency with other formats
    """
    return extract_format3_data(pdf_path)


def pair_invoice_consignment(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Match Invoice pages with their Consignment pages.
    Pages come in pairs: Invoice + Consignment (order may vary).
    Returns list of paired records with combined data.
    
    Field names match format2_mapping.json (database field names):
    Branch, Date, ConsignmentNo, Source, Destination, Vehicle, EWayBillNo,
    Consignor, Consignee, GSTType, Delivery Address, Invoice No, ContentName,
    ActualWeight, E-WayBill ValidUpto, Invoice Date, E-Way Bill NO
    """
    invoices = [p for p in pages if p.get("type") == "INVOICE"]
    consignments = [p for p in pages if p.get("type") == "CONSIGNMENT"]
    
    records = []
    
    # Simple sequential pairing: assume pages are ordered
    for i, inv in enumerate(invoices):
        record = {
            # From Invoice page - Using database field names from format2_mapping.json
            "Branch": inv.get("branch"),
            "Source": inv.get("branch"),  # Same as Branch for consignor location
            "Date": inv.get("invoice_date"),
            "Invoice Date": inv.get("invoice_date"),
            "Invoice No": inv.get("invoice_number"),
            "Destination": inv.get("destination"),
            "Vehicle": inv.get("vehicle_no"),
            "EWayBillNo": inv.get("eway_bill_no"),
            "E-Way Bill NO": inv.get("eway_bill_no"),
            "E-WayBill ValidUpto": inv.get("eway_date"),
            "E-Way Bill Date": inv.get("invoice_date"),
            "GSTType": "Unregistered",
            "ContentName": inv.get("product_category"),
            "Consignor": inv.get("consignor"),
            "Consignee": inv.get("consignee"),
            "Delivery Address": inv.get("delivery_address"),
            "ActualWeight": inv.get("actual_weight"),
            
            # From Consignment page (if available)
            "ConsignmentNo": consignments[i].get("gc_number") if i < len(consignments) else None,
        }
        records.append(record)
    
    return records


def run(pdf_path: str) -> Dict[str, Any]:
    """
    FastAPI entry point for Format 3 extraction.
    Returns raw_data dictionary for transformation.
    
    This function:
    1. Extracts all pages using extract_format3_data()
    2. Pairs Invoice + Consignment pages
    3. Applies data transformation from database mappings
    4. Returns the FIRST record's raw_data (single invoice mode)
    """
    result = extract_format3_data(pdf_path)
    
    if result.get("status") != "success":
        return {"error": result.get("error_message", "Extraction failed")}
    
    # Pair Invoice + Consignment pages
    records = pair_invoice_consignment(result.get("pages", []))
    
    if not records:
        return {"error": "No valid Invoice+Consignment pairs found"}
    
    # Get first record for single-invoice mode
    raw_data = records[0]
    
    # ============================================
    # DATA TRANSFORMATION (Check database mappings)
    # ============================================
    logger.info("=" * 60)
    logger.info("DATA TRANSFORMATION: Checking database mappings...")
    logger.info("=" * 60)
    
    try:
        from .data_transformation import transform_extracted_data
        
        transformation_result = transform_extracted_data(raw_data)
        
        if transformation_result["transformed"]:
            logger.info("[OK] Data transformation completed:")
            for change in transformation_result["changes"]:
                logger.info(f"  * {change['field']}: '{change['from']}' -> '{change['to']}'")
            # Update raw_data with transformed values
            raw_data = transformation_result["data"]
        else:
            logger.info("[OK] No data transformations needed")
    
    except ImportError as e:
        logger.warning("[WARN] Data transformation module not available: %s", e)
        logger.warning("  Skipping data transformation step")
    except Exception as e:
        logger.error("[ERR] Data transformation failed: %s", e, exc_info=True)
        logger.warning("  Returning original extracted data without transformation")
    
    # Return transformed (or original) data
    return raw_data


def save_results_to_txt(result: Dict[str, Any], output_path: str):
    """Save extraction results to a formatted text file for verification"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("FORMAT 3 EXTRACTION RESULTS - PAGE BY PAGE\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Extraction Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Pages: {result.get('total_pages', 0)}\n")
        f.write(f"Invoice Pages: {result.get('invoice_pages', 0)}\n")
        f.write(f"Consignment Pages: {result.get('consignment_pages', 0)}\n\n")
        f.write("=" * 60 + "\n\n")
        
        for page in result.get("pages", []):
            if page.get("type") == "CONSIGNMENT":
                f.write(f"Page {page['page']:2}: CONSIGNMENT\n")
                f.write(f"         GC Number: {page.get('gc_number')}\n\n")
            elif page.get("type") == "INVOICE":
                f.write(f"Page {page['page']:2}: INVOICE\n")
                f.write(f"         Invoice No: {page.get('invoice_number')}\n")
                f.write(f"         Consignor: {page.get('consignor')}\n")
                f.write(f"         Consignee: {page.get('consignee')}\n")
                f.write(f"         Branch: {page.get('branch')}\n")
                f.write(f"         Invoice Date: {page.get('invoice_date')}\n")
                f.write(f"         Destination: {page.get('destination')}\n")
                f.write(f"         Vehicle No: {page.get('vehicle_no')}\n")
                f.write(f"         E-Way Bill: {page.get('eway_bill_no')}\n")
                f.write(f"         E-Way Date: {page.get('eway_date')}\n")
                f.write(f"         PAN NO: {page.get('pan_no')}\n")
                f.write(f"         GST No: {page.get('gst_no')}\n")
                f.write(f"         Product Category: {page.get('product_category')}\n")
                f.write(f"         Actual Weight: {page.get('actual_weight')}\n")
                f.write(f"         Address: {page.get('delivery_address')}\n\n")
                
        f.write("=" * 60 + "\n")
        f.write(f"Status: {result.get('status')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Extraction Time: {result.get('extraction_timestamp')}\n")
        f.write(f"Total Pages: {result.get('total_pages')}\n")
        f.write(f"Invoice Pages: {result.get('invoice_pages')}\n")
        f.write(f"Consignment Pages: {result.get('consignment_pages')}\n")
        f.write("\n" + "=" * 60 + "\n\n")
        
        for page_data in result.get("pages", []):
            page_num = page_data.get("page")
            page_type = page_data.get("type")
            
            f.write(f"Page {page_num:2d}: {page_type}\n")
            
            if page_type == "CONSIGNMENT":
                gc = page_data.get("gc_number") or "NOT FOUND"
                f.write(f"         GC Number: {gc}\n")
            elif page_type == "INVOICE":
                branch = page_data.get("branch") or "-"
                date = page_data.get("invoice_date") or "-"
                destination = page_data.get("destination") or "-"
                vehicle = page_data.get("vehicle_no") or "-"
                eway = page_data.get("eway_bill_no") or "-"
                eway_dt = page_data.get("eway_date") or "-"
                pan = page_data.get("pan_no") or "-"
                gst = page_data.get("gst_no") or "-"
                prod_cat = page_data.get("product_category") or "-"
                consignor = page_data.get("consignor") or "-"
                consignee = page_data.get("consignee") or "-"
                weight = page_data.get("actual_weight") or "-"
                f.write(f"         Consignor: {consignor}\n")
                f.write(f"         Consignee: {consignee}\n")
                f.write(f"         Branch: {branch}\n")
                f.write(f"         Invoice Date: {date}\n")
                f.write(f"         Destination: {destination}\n")
                f.write(f"         Vehicle No: {vehicle}\n")
                f.write(f"         E-Way Bill: {eway}\n")
                f.write(f"         E-Way Date: {eway_dt}\n")
                f.write(f"         PAN NO: {pan}\n")
                f.write(f"         GST No: {gst}\n")
                f.write(f"         Product Category: {prod_cat}\n")
                f.write(f"         Actual Weight: {weight}\n")
            f.write("\n")
        
        f.write("=" * 60 + "\n")
        f.write(f"Status: {result.get('status')}\n")


# -------------------------
# Test/Demo
# -------------------------
if __name__ == "__main__":
    import sys
    
    # Test file path
    test_pdf = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    output_txt = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\format3_page_results.txt"
    
    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
    
    print("=" * 80)
    print("FORMAT 3 EXTRACTOR - PAGE BY PAGE")
    print("=" * 80)
    print(f"PDF: {os.path.basename(test_pdf)}")
    print()
    
    # Extract
    result = extract_format3_data(test_pdf)
    
    # Save to txt
    save_results_to_txt(result, output_txt)
    print(f"\nResults saved to: {output_txt}")
    
    # Display summary
    print("\nSUMMARY:")
    print(f"  Total Pages: {result.get('total_pages')}")
    print(f"  Invoice Pages: {result.get('invoice_pages')}")
    print(f"  Consignment Pages: {result.get('consignment_pages')}")
    print(f"  Status: {result.get('status')}")
    print("=" * 80)
