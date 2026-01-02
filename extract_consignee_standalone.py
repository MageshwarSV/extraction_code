# extract_consignee_standalone.py
# Extracts Consignee company name using dual OCR comparison approach
# Compares deskewed vs raw image OCR and picks the best result

import os
import sys
import re
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from difflib import SequenceMatcher

sys.path.insert(0, os.getcwd())
from engine.extractors.deskew import deskew_and_enhance

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\consignee_extracted.txt"


def is_valid_company_name(text):
    """Check if text looks like a valid company name."""
    if not text or len(text) < 8:  # Reduced minimum length to support shorter names
        return False
    # Count alphabetic characters
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < len(text) * 0.5: # Slightly more lenient alpha ratio
        return False
    # Reject if too many spaces
    space_count = text.count(' ')
    if space_count > len(text) / 3:
        return False
    # Reject weird patterns
    if re.search(r'[^A-Za-z0-9\s\(\)\-]{3,}', text):
        return False
    
    text_upper = text.upper().strip()
    # Broaden the suffix list to include diverse business types
    suffixes = ['LTD', 'LIMITED', 'PVT LTD', 'PRIVATE LIMITED', 'PRIVATE LTD', 
                'INC', 'CORP', 'METALS', 'CEMENT', 'STEEL', 'SOLUTIONS', 
                'WORKS', 'SERVICES', 'SYSTEMS', 'TECHNOLOGIES', 'ENTERPRISES',
                'INDUSTRIES', 'INFRASTRUCTURES', 'BLUE METALS']
    
    # Check for company suffixes AT THE END or as standalone words
    # Handle hyphenated names
    base_name = text_upper.split('-')[0].strip() if '-' in text_upper else text_upper
    has_suffix = any(base_name.endswith(s) or text_upper.endswith(s) for s in suffixes)
    
    has_india_paren = '(INDIA)' in text_upper or 'INDIA)' in text_upper
    # Also allow if it's a multi-word uppercase string that doesn't look like an address
    is_caps_sequence = len(text_upper.split()) >= 2 and text_upper.isupper()
    
    return has_suffix or has_india_paren or is_caps_sequence


def score_company_name(text):
    """Score a company name based on OCR quality indicators."""
    if not text:
        return 0
    
    score = 0
    text_upper = text.upper()
    
    # Base score for length
    score += min(len(text) / 5, 10)
    
    # Bonus for valid company suffixes at end
    suffixes = ['PVT LTD', 'PRIVATE LIMITED', 'LIMITED', 'LTD', 'METALS', 'CEMENT', 'STEEL', 
                'SOLUTIONS', 'WORKS', 'SERVICES', 'TECHNOLOGIES', 'METALS']
    
    base_name = text_upper.split('-')[0].strip() if '-' in text_upper else text_upper
    for suffix in suffixes:
        if base_name.endswith(suffix) or text_upper.endswith(suffix):
            score += 20
            break
    
    # Bonus for (INDIA) pattern
    if re.search(r'\([A-Z]+\)', text_upper):
        score += 15
    
    # Penalty for address-like keywords
    address_keywords = ['ROAD', 'VILLAGE', 'VILL', 'STREET', 'ST', 'MAIN', 'FLR', 'FLOOR', 'POST', 'DIST', 'DISTRICT']
    for kw in address_keywords:
        if f' {kw}' in text_upper or f'{kw} ' in text_upper:
            score -= 10
    
    # Penalty for starting with ) which indicates OCR error
    if text.strip().startswith(')'):
        score -= 20
    
    return score


def extract_company_from_ocr_text(ocr_text):
    """Extract the best company name candidate from OCR text."""
    candidates = []
    
    # Negative words to filter out lines that are likely addresses
    negative_patterns = [
        r'\d{6}', # Pincode
        r'ROAD', r'STREET', r'VILLAGE', r'VILL', r'DIST', r'POST',
        r'BENGALURU', r'CHENNAI', r'HYDERABAD', r'PUNE', r'MUMBAI', r'DELHI',
        r'TAMIL\s*NADU', r'KARNATAKA', r'MAHARASHTRA', r'TELANGANA',
        r'STATE\s*\d', r'SY\s*NO'
    ]
    
    for line in ocr_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Skip header/label lines
        lower = line.lower()
        if any(x in lower for x in ['recipient', 'consignee', 'address', 'sales', 'category', 'dc.no', 'yc.no']):
            continue
        
        # Filter out address lines using negative patterns
        if any(re.search(pat, line, re.IGNORECASE) for pat in negative_patterns):
            continue
            
        # Clean the line
        line = re.sub(r'[\|\\\:\]\[,]+$', '', line).strip()
        line = re.sub(r'\s+[A-Za-z]$', '', line).strip()
        
        if is_valid_company_name(line):
            candidates.append((line, score_company_name(line)))
    
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    return ""


def find_header_y(image_cv):
    """Find the exact Y-coordinate of the bottom of the 'Recipient / Consignee' header."""
    # Use image_to_data to find the text position
    data = pytesseract.image_to_data(image_cv, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    header_bottom_y = None
    max_conf = 0
    
    for i in range(len(data['text'])):
        text = data['text'][i].lower()
        if not text:
            continue
            
        # Look for 'recipient' or 'consignee'
        if 'recipi' in text or 'consign' in text:
            y = data['top'][i] + data['height'][i]
            conf = data['conf'][i]
            # Higher confidence is better
            if conf > max_conf:
                max_conf = conf
                header_bottom_y = y
                
    return header_bottom_y


def extract_consignee_dual_ocr(page, raw_page):
    """
    Extract consignee using precision cropping and dual OCR comparison.
    Tries to isolate the first line below the header.
    """
    # Get images as OpenCV arrays
    deskew_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
    raw_cv = cv2.cvtColor(np.array(raw_page), cv2.COLOR_RGB2BGR)
    
    height, width = deskew_cv.shape[:2]
    
    # Broad base region for header search
    y1_search, y2_search = int(height * 0.15), int(height * 0.40)
    x1, x2 = int(width * 0.40), int(width * 0.95)
    
    search_crop_deskew = deskew_cv[y1_search:y2_search, x1:x2]
    search_crop_raw = raw_cv[y1_search:y2_search, x1:x2]
    
    # Find headers
    header_y_deskew = find_header_y(search_crop_deskew)
    header_y_raw = find_header_y(search_crop_raw)
    
    def extract_from_header_y(image_full_crop, header_y):
        if header_y is None:
            return ""
        
        # Crop exactly ONE line below the header
        # Typically one line height is 40-60 pixels at 300 DPI
        line_y1 = header_y + 15 # Padding below header text line
        line_y2 = line_y1 + 75  # Height for one full line
        
        if line_y2 > image_full_crop.shape[0]:
            line_y2 = image_full_crop.shape[0]
            
        precison_crop = image_full_crop[line_y1:line_y2, :]
        gray = cv2.cvtColor(precison_crop, cv2.COLOR_BGR2GRAY)
        
        # OCR the precision crop
        text = pytesseract.image_to_string(gray, config='--psm 6').strip()
        
        # Clean the first line
        first_line = text.split('\n')[0].strip()
        first_line = re.sub(r'[\|\\\:\]\[,]+$', '', first_line).strip()
        first_line = re.sub(r'\s+[A-Z]$', '', first_line).strip()
        
        return first_line if is_valid_company_name(first_line) else ""

    # Try precision extraction
    p_deskew = extract_from_header_y(search_crop_deskew, header_y_deskew)
    p_raw = extract_from_header_y(search_crop_raw, header_y_raw)
    
    # Fallback to broader search if precision extraction returns nothing
    if not p_deskew and not p_raw:
        # Use full crop OCR and scoring as fallback
        deskew_text = pytesseract.image_to_string(cv2.cvtColor(search_crop_deskew, cv2.COLOR_BGR2GRAY), config='--psm 6')
        raw_text = pytesseract.image_to_string(cv2.cvtColor(search_crop_raw, cv2.COLOR_BGR2GRAY), config='--psm 6')
        
        p_deskew = extract_company_from_ocr_text(deskew_text)
        p_raw = extract_company_from_ocr_text(raw_text)
    
    # Pick the best one
    score_deskew = score_company_name(p_deskew)
    score_raw = score_company_name(p_raw)
    
    if score_deskew >= score_raw and p_deskew:
        return p_deskew
    else:
        return p_raw or p_deskew or ""



print("Converting PDF to images...")
pages = convert_from_path(pdf_path, dpi=300)

results = []
results.append("CONSIGNEE EXTRACTION RESULTS")
results.append("=" * 70)
results.append(f"PDF: DocScanner 23-Dec-2025 05-02 PM.pdf")
results.append("-" * 70)

for i, page in enumerate(pages, 1):
    # Check if consignment page
    rotated = page.rotate(90, expand=True)
    rotated_text = pytesseract.image_to_string(rotated, config='--psm 6')
    if 'CONSIGNMENT' in rotated_text.upper() and 'NOTE' in rotated_text.upper():
        print(f"Page {i}: CONSIGNMENT (Skipping)")
        continue
    
    print(f"Page {i}: Processing Invoice...")
    
    # Get deskewed version
    try:
        page_deskewed = deskew_and_enhance(page)
    except:
        page_deskewed = page
    
    # Extract using dual OCR comparison
    consignee = extract_consignee_dual_ocr(page_deskewed, page)
    
    if consignee:
        line = f"Page {i:2}: {consignee}"
    else:
        line = f"Page {i:2}: NOT FOUND"
    
    results.append(line)
    print(f"    -> {consignee if consignee else 'NOT FOUND'}")

results.append("=" * 70)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f"\nResults saved to: {output_file}")
