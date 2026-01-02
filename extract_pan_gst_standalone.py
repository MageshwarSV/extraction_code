
import cv2
import pytesseract
import numpy as np
import os
import re
from pdf2image import convert_from_path
from PIL import Image

# Disable decompression bomb error
Image.MAX_IMAGE_PIXELS = None

def extract_pan_gst_standalone(page_image, page_num=0, debug=True):
    """
    Extract PAN NO and GST No from Format 3 invoices.
    Uses Tesseract OCR with regex patterns.
    Returns: (pan_no, gst_no)
    """
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Full page OCR
    text = pytesseract.image_to_string(gray, config='--psm 6')
    
    if debug and page_num == 2:
        print(f"DEBUG Page {page_num} OCR Sample:\n{text[:500]}...")
    
    pan_no = None
    gst_no = None
    
    # PAN NO Pattern: 10-character alphanumeric (5 letters + 4 digits + 1 letter)
    # Example: AABCJ6731B
    pan_patterns = [
        r'PAN\s*(?:NO\.?|Number)?[:\s]*([A-Z]{5}[0-9]{4}[A-Z])',
        r'PAN\s*(?:NO\.?)?[:\s]*([A-Z0-9]{10})',  # Fallback for OCR errors
    ]
    
    for pattern in pan_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).upper()
            # Validate PAN format: 5 letters + 4 digits + 1 letter
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', val):
                pan_no = val
                if debug: print(f"DEBUG Page {page_num}: PAN Found: {pan_no}")
                break
    
    # GST NO Pattern: 15-character (2 digits + PAN + 1 digit + Z + 1 alphanumeric)
    # Example: 33AABCJ6731B1Z3
    gst_patterns = [
        r'GST\s*(?:NO\.?|Number|IN)?[:\s]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z])',
        r'GSTIN[:\s]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z])',
        r'GST\s*(?:NO\.?)?[:\s]*([0-9A-Z]{15})',  # Fallback for OCR errors
    ]
    
    for pattern in gst_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).upper()
            # Validate GST format loosely
            if len(val) == 15 and val[:2].isdigit():
                gst_no = val
                if debug: print(f"DEBUG Page {page_num}: GST Found: {gst_no}")
                break
    
    return pan_no, gst_no

if __name__ == "__main__":
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    target_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20]
    
    print("\n=== Testing PAN/GST Extraction ===")
    output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\pan_gst_results.txt"
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, page in enumerate(pages):
                p_num = i + 1
                if p_num not in target_pages: continue
                
                pan, gst = extract_pan_gst_standalone(page, page_num=p_num, debug=True)
                print(f"Page {p_num}: PAN={pan}, GST={gst}")
                f.write(f"Page {p_num}: PAN={pan}, GST={gst}\n")
    except Exception as e:
        print(f"Error: {e}")
