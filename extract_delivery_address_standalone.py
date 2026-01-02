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

# Tesseract configuration
# Rely on system PATH as configured in main project

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

def piecewise_deskew(image, points, target_y=20, crop_height=300):
    """
    Straighten image based on control points.
    Increased crop_height to capture the full address block below the header.
    """
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
    cleaned = []
    # Skip the first line (Consignee Name) as strict requested? 
    # User said "delivery address as consignee you see the same line but in this ending line is india"
    # Usually Consignee Name is line 0. Address starts line 1.
    
    stop_found = False
    
    # Skip line 0 (Company Name)
    address_content = lines[1:] 
    
    final_lines = []
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
            
    if not stop_found:
        # If we didn't find INDIA, maybe we consumed everything?
        pass
        
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

def extract_delivery_address_format3(page_image, page_num=0, debug=True):
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    # Search area
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
        # Start Y: 45 (approx below header) 
        # End Y: We crop deep, then cut at text logic
        crop_y1 = 45
        crop_y2 = 450 # Go deep enough to catch "INDIA"
        
        # X range - same as consignee
        crop_x1 = max(0, hx_start - int(hw * 0.05)) # Slightly tighter left
        crop_x2 = min(search_area.shape[1], header_points[-1]['right'] + int(hw * 1.0)) # Wide right
        
        raw_crop = straightened[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if debug:
             debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_address"
             if not os.path.exists(debug_dir): os.makedirs(debug_dir)
             cv2.imwrite(os.path.join(debug_dir, f"page_{page_num}_address_raw.png"), raw_crop)
        
        # OCR
        gray = cv2.cvtColor(raw_crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR with layout analysis (PSM 6)
        text = pytesseract.image_to_string(thresh, config='--psm 6')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if not lines:
            return ""
            
        # Extract until INDIA
        address = clean_address_lines(lines)
        return address
        
    return ""

if __name__ == "__main__":
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    
    # Process only Invoice pages known (e.g. 2, 4, 6, 8, 10, 11)
    # as per previous run
    # Process all Invoice pages found in Format 3 document
    target_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20] 
    
    print("Converting specific pages...")
    # Loading specific pages is tricky with pdf2image index, so we load all
    pages = convert_from_path(pdf_path, dpi=300)
    
    print(f"Total pages: {len(pages)}")
    
    output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_addr_results"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    with open(os.path.join(output_dir, "results.txt"), "w") as f:
        for i, page in enumerate(pages):
            p_num = i + 1
            if p_num not in target_pages: continue
            
            print(f"Processing Page {p_num}...")
            addr = extract_delivery_address_format3(page, page_num=p_num, debug=True)
            print(f"Page {p_num} Address:\n{addr}\n-------------------")
            
            f.write(f"Page {p_num}:\n{addr}\n\n-------------------\n")
