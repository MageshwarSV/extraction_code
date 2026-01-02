import cv2
import pytesseract
import numpy as np
import os
import re
from pdf2image import convert_from_path
from difflib import SequenceMatcher

# Disable decompression bomb error
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

# Rely on system PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def fuzzy_match(s1, s2, threshold=0.7):
    return SequenceMatcher(None, s1, s2).ratio() > threshold

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
                print(f"DEBUG: Found with {name} PSM {psm}: {match.group(0)}")
                return match.group(0)
                
    # If all strict checks fail, try loose digit extraction on the best looking image (OTSU)
    # and see if we have exactly 10 digits
    processed = strategies[0][1](gray)
    text = pytesseract.image_to_string(processed, config='--psm 6')
    digits = re.sub(r'\D', '', text)
    if len(digits) == 10:
        return digits
        
    return ""

def extract_invoice_number_standalone(page_image, page_num=0, debug=True):
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Restrict search to top half
    search_h = int(height * 0.5)
    search_img = img_cv[0:search_h, :]
    
    # 1. Detect "Internal Number" anchor
    data = pytesseract.image_to_data(search_img, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    anchor_rect = None
    
    # Look for "Internal" and "Number" close to each other
    internal_indices = []
    number_indices = []
    
    for i, text in enumerate(data['text']):
        text = text.lower().strip()
        if not text: continue
        
        if fuzzy_match(text, "internal", 0.8):
            internal_indices.append(i)
        elif fuzzy_match(text, "number", 0.8) or fuzzy_match(text, "no", 0.9): # Handle "Internal No"
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
             debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\invoice_number"
             if not os.path.exists(debug_dir): os.makedirs(debug_dir)
             cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_inv_raw.png"), roi)
        
        # Use Robust OCR
        return robust_invoice_ocr(roi)
             
    return ""
             
    return ""

if __name__ == "__main__":
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    target_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20] 
    
    print("Converting pages...")
    pages = convert_from_path(pdf_path, dpi=300)
    
    output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\invoice_number_results"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    with open(os.path.join(output_dir, "results.txt"), "w") as f:
        for i, page in enumerate(pages):
            p_num = i + 1
            if p_num not in target_pages: continue
            
            print(f"Processing Page {p_num}...")
            val = extract_invoice_number_standalone(page, page_num=p_num, debug=True)
            print(f"Page {p_num} Internal Number: {val}")
            f.write(f"Page {p_num}: {val}\n")
