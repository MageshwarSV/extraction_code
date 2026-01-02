# debug_consignee_crops.py (v3)
# Fuzzy matching for "Recipient / Consignee's Name & Address" header
# Extracts only the first line (company name) below the header

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
output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\consignee_crops"

os.makedirs(output_dir, exist_ok=True)


def fuzzy_match(text, target, threshold=0.6):
    """Check if text fuzzy matches target"""
    return SequenceMatcher(None, text.lower(), target.lower()).ratio() >= threshold


def find_header_fuzzy(data, height, width):
    """
    Find "Recipient / Consignee's Name & Address" header using fuzzy matching.
    Returns (y_position, x_position) of the header.
    """
    n = len(data['text'])
    
    # Build lines from OCR data (group words by similar y position)
    lines = {}
    for i in range(n):
        text = data['text'][i].strip()
        if not text:
            continue
        y = data['top'][i]
        # Group by y position (within 20 pixels)
        y_key = (y // 20) * 20
        if y_key not in lines:
            lines[y_key] = []
        lines[y_key].append({
            'text': text,
            'left': data['left'][i],
            'top': data['top'][i],
            'width': data['width'][i],
            'height': data['height'][i]
        })
    
    # Search for the header in each line - ONLY in top 50% of page
    target_words = ['recipient', 'consignee', 'name', 'address']
    max_y_for_header = height * 0.50  # Search in top 50% of page
    
    # Also try to find "Sales Category" as an anchor - Consignee header is just below it
    sales_category_y = None
    for y_key in sorted(lines.keys()):
        if y_key > max_y_for_header:
            continue
        line_words = lines[y_key]
        line_text = ' '.join([w['text'] for w in line_words]).lower()
        if 'sales' in line_text and 'category' in line_text:
            sales_category_y = y_key
            print(f"    Found 'Sales Category' anchor at y={y_key}")
            break
    
    for y_key in sorted(lines.keys()):
        # Skip if this line is in the bottom portion of the page
        if y_key > max_y_for_header:
            continue
            
        line_words = lines[y_key]
        line_text = ' '.join([w['text'] for w in line_words]).lower()
        
        # Skip if this is "ORIGINAL FOR RECIPIENT" at the top
        if 'original' in line_text:
            continue
        
        # Skip lines with "authorised" or "signatory" (signature area)
        if 'authoris' in line_text or 'signatory' in line_text:
            continue
        
        # Count how many target words are found (exact or fuzzy)
        matches = 0
        for target in target_words:
            for word in line_words:
                if fuzzy_match(word['text'], target, 0.7):
                    matches += 1
                    break
        
        # If we found at least 1 target word - be more lenient
        if matches >= 1:
            # Check if any word contains 'consignee' or 'recipient' (partial match)
            has_key_word = any('consign' in w['text'].lower() or 'recipi' in w['text'].lower() for w in line_words)
            if has_key_word or matches >= 2:
                # Find the rightmost position (Consignee section is on right side)
                rightmost_word = max(line_words, key=lambda w: w['left'])
                
                # Accept if it's on the right portion of the page
                if rightmost_word['left'] > width * 0.35:
                    print(f"    Fuzzy matched header at y={y_key}: '{line_text[:60]}'")
                    return y_key, line_words[0]['left'], rightmost_word['height']
    
    # Fallback: If we found Sales Category anchor, estimate header position below it
    if sales_category_y is not None:
        estimated_header_y = sales_category_y + 40  # Header is about 40 pixels below Sales Category
        print(f"    Using Sales Category anchor, estimated header at y={estimated_header_y}")
        return estimated_header_y, int(width * 0.45), 30
    
    return None, None, None


def crop_consignee_line(img_cv, header_y, header_height):
    """
    Crop the company name line below the header - with more height.
    """
    height, width = img_cv.shape[:2]
    
    # Start just below the header, capture about 100 pixels (enough for one line)
    y1 = header_y + header_height + 2
    y2 = min(height, y1 + 100)  # Increased from 80 to 100
    
    # The consignee section is on the RIGHT side (about 40-98% of width)
    x1 = int(width * 0.40)  # More left to not miss content
    x2 = int(width * 0.98)
    
    crop = img_cv[y1:y2, x1:x2]
    return crop


print("Converting PDF to images...")
pages = convert_from_path(pdf_path, dpi=300)

for i, page in enumerate(pages, 1):
    # Check if consignment page
    rotated = page.rotate(90, expand=True)
    rotated_text = pytesseract.image_to_string(rotated, config='--psm 6')
    if 'CONSIGNMENT' in rotated_text.upper() and 'NOTE' in rotated_text.upper():
        print(f"Page {i}: CONSIGNMENT (Skipping)")
        continue
    
    print(f"Page {i}: Processing Invoice...")
    
    # Deskew
    try:
        page_corrected = deskew_and_enhance(page)
    except Exception as e:
        print(f"    Deskew failed: {e}")
        page_corrected = page
    
    # Convert to OpenCV
    img_cv = cv2.cvtColor(np.array(page_corrected), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Get OCR data with bounding boxes
    data = pytesseract.image_to_data(img_cv, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    # Find header using fuzzy matching
    header_y, header_x, header_height = find_header_fuzzy(data, height, width)
    
    if header_y is not None:
        # Crop just the company name line
        crop = crop_consignee_line(img_cv, header_y, header_height or 30)
        
        # Save crop
        crop_path = os.path.join(output_dir, f"page{i:02d}_consignee_line.png")
        cv2.imwrite(crop_path, crop)
        print(f"    Saved: {crop_path}")
        
        # Also save a slightly larger context crop for verification
        y1_ctx = max(0, header_y - 10)
        y2_ctx = min(height, header_y + 100)
        x1_ctx = int(width * 0.42)
        x2_ctx = int(width * 0.98)
        context_crop = img_cv[y1_ctx:y2_ctx, x1_ctx:x2_ctx]
        context_path = os.path.join(output_dir, f"page{i:02d}_consignee_context.png")
        cv2.imwrite(context_path, context_crop)
    else:
        print(f"    Header NOT found - fallback crop")
        # Fallback: Use estimated position with more height - generous crop
        y1 = int(height * 0.14)   # Start earlier
        y2 = int(height * 0.38)   # End later (24% of page height)
        x1 = int(width * 0.38)    # More left to not miss content
        x2 = int(width * 0.98)
        crop = img_cv[y1:y2, x1:x2]
        crop_path = os.path.join(output_dir, f"page{i:02d}_consignee_fallback.png")
        cv2.imwrite(crop_path, crop)
        print(f"    Fallback saved: {crop_path}")

print(f"\nAll crops saved to: {output_dir}")
