# extract_consignee_precision_crops.py
# Implements precision cropping based strictly on the 'Recipient / Consignee' header position.
# Saves crops to a separate folder for manual inspection.

import os
import sys
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Ensure project root is in path
sys.path.insert(0, os.getcwd())
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\precision_consignee"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def clean_trailing_noise(text):
    """Strip noise and unwanted artifacts from the end of the extracted name."""
    if not text:
        return text
    text = text.strip()
    
    # 1. Strip non-alphanumeric trailing characters (symbols)
    text = re.sub(r'[^a-zA-Z0-9)\]]+$', '', text).strip()
    
    # 2. Handle cases like "COMPANY LIMITED x" or "COMPANY LTD v"
    # If the text is mostly uppercase and ends with a single lowercase letter or single char after space
    # (Checking for single letter 'x', 'v', 'i', etc. that often come from boundary noise)
    if len(text) > 3:
        # Match a single char (often lowercase or noise) preceded by a space at the end
        text = re.sub(r'\s+[a-z0-9]$', '', text).strip()
        # Also catch just a floating 'x' or similar if it's definitely noise
        text = re.sub(r'\s+[xX]$', '', text).strip()
        
    return text.strip()

def get_header_points(image_cv):
    """Find multiple points along the 'Recipient / Consignee' header to detect curvature."""
    data = pytesseract.image_to_data(image_cv, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    n_boxes = len(data['text'])
    points = []
    
    for i in range(n_boxes):
        text = data['text'][i].lower().strip()
        if not text:
            continue
            
        if 'recip' in text or 'consign' in text:
            if data['conf'][i] > 25:
                # Add (x, y) point - center of the box
                points.append({
                    'x': data['left'][i] + data['width'][i] // 2,
                    'y': data['top'][i] + data['height'][i] // 2,
                    'left': data['left'][i],
                    'right': data['left'][i] + data['width'][i],
                    'top': data['top'][i],
                    'height': data['height'][i]
                })
    
    if not points:
        return None
        
    # Filter points to only include those on the main header line
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
    # Create a map for cv2.remap
    map_x = np.zeros((crop_height, w), np.float32)
    map_y = np.zeros((crop_height, w), np.float32)

    if len(points) < 2:
        # Fallback: Just vertical shift based on the single point
        local_y = points[0]['y']
        for cy in range(crop_height):
            for x in range(w):
                map_x[cy, x] = x
                map_y[cy, x] = local_y + (cy - target_y)
    else:
        # Use linear interpolation/extrapolation to find y-offset at any x
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        
        # Fill maps
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
            
            # Move local_y to target_y in the new crop
            for cy in range(crop_height):
                map_x[cy, x] = x
                map_y[cy, x] = local_y + (cy - target_y)
            
    straightened = cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return straightened

def process_pdf():
    print("Converting PDF to images...")
    pages = convert_from_path(pdf_path, dpi=300)
    
    extraction_results = []
    
    for i, page in enumerate(pages, 1):
        # Basic check for invoice (not consignment note)
        rotated = page.rotate(90, expand=True)
        check_text = pytesseract.image_to_string(rotated, config='--psm 6')
        if 'CONSIGNMENT' in check_text.upper():
            print(f"Page {i}: Skipping Consignment Note")
            continue
            
        print(f"Page {i}: Searching for Consignee header...")
        img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]
        
        # Search area: upper right quadrant approximately
        search_y1, search_y2 = int(height * 0.15), int(height * 0.45)
        search_x1, search_x2 = int(width * 0.40), int(width * 0.98)
        
        search_area = img_cv[search_y1:search_y2, search_x1:search_x2]
        header_points = get_header_points(search_area)
        
        if header_points:
            # Step 1: Divide into segments and straighten based on points
            # Header boundaries
            hx_start = header_points[0]['left']
            hx_end = header_points[-1]['right']
            hw = hx_end - hx_start
            
            # Define broad crop area relative to search_area
            # Left expansion 15%, Right expansion 150%
            # IMPORTANT: Expansion is relative to hx_start and hw
            final_x1 = max(0, hx_start - int(hw * 0.15))
            final_x2 = min(search_area.shape[1], hx_start + int(hw * 3.0)) # wide enough for name
            
            # The piecewise_deskew will handle the "bend" across this whole width
            straightened = piecewise_deskew(search_area, header_points, target_y=20, crop_height=125)
            
            # Now crop horizontally and vertically from the straightened strip
            # Line below header starts around 55px down (header is at 20, height ~35)
            crop_y1 = 55
            crop_y2 = crop_y1 + 65
            
            if final_x1 >= final_x2: final_x2 = final_x1 + 10 # Safety
            
            precision_crop = straightened[crop_y1:crop_y2, final_x1:final_x2]
            
            if precision_crop.size == 0:
                print(f"  -> Page {i}: Empty precision crop!")
                extraction_results.append(f"Page {i:2}: ERROR_EMPTY_CROP")
                continue

            # Save the crop
            crop_name = f"page_{i}_consignee_crop.png"
            crop_path = os.path.join(output_dir, crop_name)
            cv2.imwrite(crop_path, precision_crop)
            
            # OCR the precision crop
            gray = cv2.cvtColor(precision_crop, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            raw_name = lines[0] if lines else "NOT_READABLE"
            extracted_name = clean_trailing_noise(raw_name)
            
            print(f"  -> Extracted: {extracted_name}")
            extraction_results.append(f"Page {i:2}: {extracted_name}")
        else:
            print(f"  -> Header NOT found on Page {i}")
            extraction_results.append(f"Page {i:2}: HEADER_NOT_FOUND")

    # Write summary
    with open(os.path.join(output_dir, "precision_results.txt"), "w") as f:
        f.write("\n".join(extraction_results))

if __name__ == "__main__":
    process_pdf()
