import cv2
import pytesseract
import numpy as np
import os
import re
from pdf2image import convert_from_path

# Disable decompression bomb error
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

def extract_actual_weight_standalone(page_image, page_num=0, debug=True):
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    
    debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\actual_weight"
    if not os.path.exists(debug_dir): 
        os.makedirs(debug_dir)
    
    # Crop focused region (30-65% vertical) - Expand top for Page 4, limit bottom for Page 14/15
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
            # Patterns: rate, per mt, er mt, te per
            if ('rate' in t) or ('per' in t and 'mt' in t) or ('er' in t and 'mt' in t):
                anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                anchor_type = 'rate'
                if debug: print(f"DEBUG Page {page_num}: Found Anchor 'Rate' ({text}) at ({anchor['left']}, {anchor['top']})")
                break
                
            # Anchor 2: "Packing" (or "Packing Type") -> Qty is RIGHT
            # Patterns: packing, cking, type
            if 'packing' in t or 'cking' in t:
                anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                anchor_type = 'packing'
                if debug: print(f"DEBUG Page {page_num}: Found Anchor 'Packing' ({text}) at ({anchor['left']}, {anchor['top']})")
                break

            # Anchor 3: "Amount" (far right) -> Qty is 2 columns LEFT
            if 'amount' in t and ('net' not in t):
                 anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                 anchor_type = 'amount'
                 if debug: print(f"DEBUG Page {page_num}: Found Anchor 'Amount' ({text}) at ({anchor['left']}, {anchor['top']})")
                 break

            # Anchor 4: "HSN" 
            if 'hsn' in t:
                 anchor = {'left': data['left'][i], 'top': data['top'][i], 'width': data['width'][i], 'height': data['height'][i]}
                 anchor_type = 'hsn'
                 # Keep searching for better anchor, but use this if nothing else
                 
        if anchor:
            # Calculate Qty Box based on Anchor Type (Rel to REGION)
            crop_y1 = anchor['top'] + anchor['height'] + 5
            crop_y2 = min(region.shape[0], crop_y1 + 100) # Look below header
            
            if anchor_type == 'rate':
                # Rate is R of Qty. 
                # Reduce x2 to exclude the vertical line and Rate text.
                # anchor['left'] is start of Rate text.
                crop_x2 = max(0, anchor['left'] - 5) 
                crop_x1 = max(0, anchor['left'] - 230)
                
            elif anchor_type == 'packing':
                # Packing is left of Qty. Look RIGHT.
                # Reduced width to 150 (was 300) to avoid hitting Rate column (Page 14 issue)
                # Adaptive loop will expand right if needed.
                crop_x1 = anchor['left'] + anchor['width'] + 5
                crop_x2 = min(region.shape[1], crop_x1 + 150)
                
            elif anchor_type == 'amount':
                # Amount is far right. 
                # Reverted to 750px as crop was correct visually.
                crop_x2 = max(0, anchor['left'] - 350) 
                crop_x1 = max(0, anchor['left'] - 750)
                
            elif anchor_type == 'hsn':
                 crop_x1 = max(0, anchor['left'] + 400) 
                 crop_x2 = min(region.shape[1], crop_x1 + 400)

            roi = region[crop_y1:crop_y2, crop_x1:crop_x2]
            
            # Adaptive Expansion Loop (Smart Directional)
            # Strategy:
            # 1. Start with 0 expansion.
            # 2. Analyze result:
            #    - If Ends with incomplete decimal (e.g. '35.0', '35.00') -> Expand RIGHT incrementally
            #    - If Starts with decimal (e.g. '.160', '0.160' but expected 40.160) -> Expand LEFT incrementally
            # 3. Stop if perfect match (\d+\.\d{3}) found.
            
            # Initial Run
            valid_weight = None
            best_weight = None
            
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
                
                # EasyOCR
                try:
                     if 'reader_obj' not in globals():
                        global reader_obj
                        import easyocr
                        reader_obj = easyocr.Reader(['en'], verbose=False)
                     results = reader_obj.readtext(roi_padded_curr)
                     for (bbox, text, prob) in results:
                        txt = text.replace(" ", "").replace(",", ".")
                        m = re.search(r'(\d*\.?\d+)', txt) # Capture broader pattern
                        if m: return m.group(1)
                except: pass
                
                # Tesseract
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
            
            # Max iterations (Increased to 50 -> 100px expansion as per user request to catch Page 14)
            for i in range(50): 
                val = try_ocr(current_left, current_right)
                
                if debug and (i % 5 == 0 or val): # Reduce debug spam
                    print(f"DEBUG Page {page_num} Iter {i} (L{current_left}, R{current_right}): {val}")
                
                if val:
                    # HEURISTIC: User confirms trailing '1' is likely a vertical line artifact -> Replace with '0'
                    if val.endswith('1') and "." in val and len(val.split(".")[1]) == 3:
                        if debug: print(f"DEBUG Page {page_num} Correcting trailing '1' to '0': {val} -> {val[:-1]}0")
                        val = val[:-1] + '0'

                    # Check for perfect match (3 decimals)
                    if re.match(r'^\d+\.\d{3}$', val):
                        return val # Success!
                    
                    # Update best
                    if not best_weight or len(val) > len(best_weight):
                        best_weight = val
                    
                    # Decide Direction
                    # Case 1: Missing Tail (xx. or xx.x or xx.xx)
                    # Regex: Ends with dot or dot+1/2 digits
                    if re.search(r'\.\d{0,2}$', val):
                        current_right += 2 # Expand Right
                        continue

                    # Case 2: Missing Head (.xxx or x.xxx where x is partial?)
                    # Harder to detect "partial x". 
                    # But if it starts with dot, definitely expand left.
                    if val.startswith('.'):
                        current_left += 2 # Expand Left
                        continue
                        
                    # If we have something like '0.160' but it should be '40.160' (Length check?)
                    # If val is small (len < 5) and has 3 decimals?
                    # e.g. 0.160 (len 5). 40.160 (len 6).
                    # If user implies "5 value get only", maybe len < 5?
                    # Let's assume strict 3-decimal check is the goal.
                    # If we have 3 decimals but suspect missing head (e.g. value is surprisingly small/short?)
                    # For now, rely on "." position.
                    
                    # If neither obvious case, maybe just try expanding both slowly?
                    # Or stop?
                    # User said "unless get the value".
                    # Let's try expanding Right default if we don't match 3 decimals?
                    # Or both?
                    # Let's increment right if we haven't found 3 decimals yet.
                    if not re.search(r'\.\d{3}$', val):
                         current_right += 2
                    else:
                         # Has 3 decimals but maybe missing head?
                         # e.g. '0.160'. 
                         # Try expanding Left just in case?
                         if current_left == 0 and len(val) < 6: # Heuristic
                              current_left += 5
                         else:
                              break # Assume done
                else:
                    # No value found. Expand both?
                    current_left += 2
                    current_right += 2
            
            # If we are here, strict match was not found for this anchor.
            # Convert 'best_weight' to 'global_best' but DO NOT return yet.
            # Continue to next anchor.

    if debug: print(f"DEBUG Page {page_num}: No stable anchor (Rate/Packing) found.")
    return ""

if __name__ == "__main__":
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    target_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20] 
    
    print("\n=== Testing DPI 300 ===")
    pages = convert_from_path(pdf_path, dpi=300)
    
    output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\actual_weight_results"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    with open(os.path.join(output_dir, "results.txt"), "w") as f:
        for i, page in enumerate(pages):
            p_num = i + 1
            if p_num not in target_pages: continue
            
            print(f"Processing Page {p_num}...")
            val = extract_actual_weight_standalone(page, page_num=p_num, debug=True)
            print(f"Page {p_num} Weight: {val}")
            f.write(f"Page {p_num}: {val}\n")
