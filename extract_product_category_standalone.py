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

def fuzzy_match_token(token, target):
    """Check if token is similar to target"""
    return SequenceMatcher(None, token.upper(), target.upper()).ratio() > 0.8

def get_header_points(img, header_text="Product"):
    """
    Find control points for the header row to enable piecewise deskewing.
    Similar to the Consignee extraction logic.
    """
    data = pytesseract.image_to_data(img, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    points = []
    for i, text in enumerate(data['text']):
        t = text.lower().strip()
        if not t: continue
        
        # Look for "Product" or "HSN" or "Name" or "Code"
        if any(kw in t for kw in ["product", "hsn", "name", "code", "packing"]):
            x = data['left'][i] + data['width'][i] // 2
            y = data['top'][i] + data['height'][i] // 2
            points.append((x, y))
            
    return points

def piecewise_deskew(img, control_points, crop_height=300):
    """
    Straighten the image using control points.
    Same technique as Consignee extraction.
    """
    if len(control_points) < 2:
        # If not enough points, return a simple crop
        h, w = img.shape[:2]
        if control_points:
            y = control_points[0][1]
            return img[max(0, y-20):min(h, y+crop_height), :]
        return img[0:min(img.shape[0], crop_height), :]
    
    # Sort by X
    control_points = sorted(control_points, key=lambda p: p[0])
    
    # Calculate average Y deviation
    avg_y = np.mean([p[1] for p in control_points])
    
    # Simple approach: take the content starting from the header row
    h, w = img.shape[:2]
    start_y = max(0, int(avg_y) - 10)
    end_y = min(h, start_y + crop_height)
    
    cropped = img[start_y:end_y, :]
    
    # Check if significant tilt exists
    if len(control_points) >= 2:
        first_y = control_points[0][1]
        last_y = control_points[-1][1]
        tilt = last_y - first_y
        
        # If tilt > 10 pixels, apply remap correction
        if abs(tilt) > 10:
            # Create a remapping array to straighten
            map_x = np.zeros((crop_height, w), dtype=np.float32)
            map_y = np.zeros((crop_height, w), dtype=np.float32)
            
            for x in range(w):
                # Interpolate offset based on position
                frac = x / max(1, w - 1)
                y_offset = tilt * frac
                
                for y in range(crop_height):
                    map_x[y, x] = x
                    map_y[y, x] = y + y_offset
                    
            cropped = cv2.remap(cropped, map_x, map_y, cv2.INTER_LINEAR)
    
    return cropped

def get_product_category(text_block):
    """
    Map extracted product description text to Category.
    """
    text_upper = text_block.upper()
    
    # 1. BOPP / LPP indicators
    if "LPP" in text_upper: return "BOPP BAG"
    if "L1PP" in text_upper: return "BOPP BAG"  # OCR error: L1PP
    if "1PP" in text_upper: return "BOPP BAG"   # OCR error
    if "IPP" in text_upper: return "BOPP BAG"   # OCR error: l->I
    if "BOPP" in text_upper: return "BOPP BAG"
    if "LAMINATED" in text_upper: return "BOPP BAG"
    if "LOMINATED" in text_upper: return "BOPP BAG"
    if "IAMINATED" in text_upper: return "BOPP BAG"
    if "WATERGUARD" in text_upper: return "BOPP BAG"  # Product name indicator
    if "WG-BG" in text_upper: return "BOPP BAG"  # Code pattern
    
    # 2. GGBS
    if "GGBS" in text_upper: return "GGBS"
    if "GG8S" in text_upper: return "GGBS"
    if "GGB5" in text_upper: return "GGBS"
    
    # 3. AD STAR
    if "AD STAR" in text_upper: return "AD STAR"
    if "ADSTAR" in text_upper: return "AD STAR"
    if "AD-STAR" in text_upper: return "AD STAR"
    
    return "UNKNOWN"

def extract_product_category_standalone(page_image, page_num=0, debug=True):
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # The Product Name table is in the MIDDLE of the page (roughly 30-60% vertically)
    # Let's crop that region first
    search_y1 = int(height * 0.35)
    search_y2 = int(height * 0.65)
    search_roi = img_cv[search_y1:search_y2, :]
    
    # Find header control points for bend correction
    header_points = get_header_points(search_roi, "Product")
    
    if debug and header_points:
        print(f"DEBUG Page {page_num}: Found {len(header_points)} header points")
    
    # Apply piecewise deskew to straighten the header row and content below
    straightened = piecewise_deskew(search_roi, header_points, crop_height=250)
    
    if debug:
        debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\product_category"
        if not os.path.exists(debug_dir): os.makedirs(debug_dir)
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_prod_straightened.png"), straightened)
    
    # OCR the straightened crop
    text = pytesseract.image_to_string(straightened, config='--psm 6')
    
    # Map to category
    category = get_product_category(text)
    
    # FALLBACK: If category is UNKNOWN, search full page text
    if category == "UNKNOWN":
        full_text = pytesseract.image_to_string(img_cv, config='--psm 6')
        category = get_product_category(full_text)
        if debug and category != "UNKNOWN":
            print(f"DEBUG Page {page_num}: Used FULL PAGE fallback -> {category}")
    
    if debug:
        # Show first 100 chars of extracted text
        clean_text = text.replace('\n', ' ').strip()[:100]
        print(f"DEBUG Page {page_num} Text: '{clean_text}' -> Category: {category}")
        
    return category

if __name__ == "__main__":
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    target_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20] 
    
    print("Converting pages...")
    pages = convert_from_path(pdf_path, dpi=300)
    
    output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\product_category_results"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    with open(os.path.join(output_dir, "results.txt"), "w") as f:
        for i, page in enumerate(pages):
            p_num = i + 1
            if p_num not in target_pages: continue
            
            print(f"Processing Page {p_num}...")
            val = extract_product_category_standalone(page, page_num=p_num, debug=True)
            print(f"Page {p_num} Category: {val}")
            f.write(f"Page {p_num}: {val}\n")
