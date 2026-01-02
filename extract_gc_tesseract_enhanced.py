
"""
Enhanced GC Number Extractor using Tesseract + Advanced OpenCV Preprocessing.
Optimized for servers with NO AVX support (where EasyOCR/RapidOCR fail).
"""
import sys
import os
import re
import cv2
import numpy as np
import logging
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.getcwd())

def preprocess_for_digits(img_pil):
    """
    Advanced preprocessing pipeline to make Tesseract see digits clearly.
    Steps:
    1. Convert to Grayscale
    2. Upscale 3x (Crucial for small numbers)
    3. Bilateral Filter (Remove noise, keep edges)
    4. Adaptive Thresholding (Handle shadows/gradients)
    5. Morphological Dilation (Thicken thin digits)
    """
    # Convert PIL to BGR (OpenCV format)
    img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Upscale (3x)
    scale = 3
    upscaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # 2. Denoise (Bilateral Filter is better than Gaussian)
    denoised = cv2.bilateralFilter(upscaled, 9, 75, 75)
    
    # 3. Adaptive Thresholding (Gaussian C)
    # Block size 31, C=2 works well for document text
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 31, 2)
    
    # 4. Optional: Dilation to thicken digits if they are faint
    # Use a very small kernel
    kernel = np.ones((2,2), np.uint8)
    dilated = cv2.erode(thresh, kernel, iterations=1) # Erode darker areas = thicken black text
    
    return dilated

def extract_gc_tesseract_enhanced(page_pil):
    """
    Try 4 rotations and finding the label, then applying enhanced OCR.
    """
    
    # 1. Try Rotations (Include 180 as per findings)
    # Production uses [90, 270], but we add 180 for this specific case
    for rotation in [180, 90, 270, 0]: 
        rotated = page_pil.rotate(rotation, expand=True)
        
        # 2. Locate Label (Standard Tesseract Pass)
        # Scan top 50%
        top_h = int(rotated.height * 0.5)
        top_region = rotated.crop((0, 0, rotated.width, top_h))
        
        logger.info(f"   [Search] Scanning Rot {rotation}° for label...")
        
        # Fast OCR to find label
        data = pytesseract.image_to_data(top_region, config='--psm 6', output_type=Output.DICT)
        
        label_found = False
        
        for i, text in enumerate(data['text']):
            if not text: continue
            
            # Expanded Regex for G.C.No variations
            if re.search(r'(G\.?C\.?N|5\.?C\.?N|6\.?C\.?N|G\.?C\.?No|GC\s*No)', text, re.IGNORECASE):
                logger.info(f"   [Label-Found] '{text}' at index {i} (conf: {data['conf'][i]})")
                label_found = True
                
                # 3. Define ROI using Production Logic (gc_number_extractor.py)
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # EXACT Prod Logic:
                # crop_x1 = gc_pos['x'] + gc_pos['w'] - 30
                # crop_y1 = gc_pos['y'] - 60
                # crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
                # crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
                
                crop_x1 = x + w + 5
                crop_y1 = max(0, y - 60)
                crop_x2 = min(top_region.width, x + w + 700)
                crop_y2 = y + h + 80
                
                roi_pil = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                
                # ADD PADDING (Crucial for edge characters like '1')
                from PIL import ImageOps
                roi_pil = ImageOps.expand(roi_pil, border=20, fill='white')
                
                # --- VISUALIZATION START ---
                # Draw boxes on a full copy to show user EXACTLY what happened
                viz_img = cv2.cvtColor(np.array(top_region), cv2.COLOR_RGB2BGR)
                
                # Red Box = Label
                cv2.rectangle(viz_img, (x, y), (x+w, y+h), (0, 0, 255), 3)
                
                # Green Box = ROI (Crop)
                cv2.rectangle(viz_img, (crop_x1, crop_y1), (crop_x2, crop_y2), (0, 255, 0), 3)
                
                viz_path = f"debug_viz_rot{rotation}.jpg"
                cv2.imwrite(viz_path, viz_img)
                logger.info(f"   [Debug] Saved Visualization: {viz_path}")
                # --- VISUALIZATION END ---

                # 4. Multi-Pass OCR Strategy
                
                # 4. Multi-Pass OCR Strategy
                variations = []
                
                # Var 1: Raw Crop (Best for clean but small text)
                variations.append(("Raw-PSM6", roi_pil, r'--psm 6 -c tessedit_char_whitelist=0123456789'))
                
                # Var 2: Scaled 3x (No other processing)
                img_np = np.array(roi_pil) 
                if len(img_np.shape) == 3: img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                variations.append(("Scaled-PSM6", scaled, r'--psm 6 -c tessedit_char_whitelist=0123456789'))
                
                # Var 3: Scaled + Threshold (Light Processing)
                _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                variations.append(("Threshold-PSM6", thresh, r'--psm 6 -c tessedit_char_whitelist=0123456789'))

                # Var 4: Scaled + PSM 7
                variations.append(("Scaled-PSM7", scaled, r'--psm 7 -c tessedit_char_whitelist=0123456789'))
                
                # --- GOLDEN CONFIG (Found via Tuning) ---
                # Scale 2x + PSM 7 + Padding (already applied)
                img_np_2x = np.array(roi_pil)
                if len(img_np_2x.shape) == 3: img_np_2x = cv2.cvtColor(img_np_2x, cv2.COLOR_RGB2GRAY)
                scaled_2x = cv2.resize(img_np_2x, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                variations.append(("Golden-2x-PSM7", scaled_2x, r'--psm 7 -c tessedit_char_whitelist=0123456789'))
                
                # --- PROVEN WINNER (from tune_padding_ocr.py) ---
                # Scale 2x + Erode + Invert + PSM 6
                kernel_erode = np.ones((2,2), np.uint8)
                eroded_2x = cv2.erode(scaled_2x, kernel_erode, iterations=1)
                _, thresh_2x = cv2.threshold(eroded_2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                inverted_2x = cv2.bitwise_not(thresh_2x)
                variations.append(("ProvenWinner-2x-Erode-Inv-PSM6", inverted_2x, r'--psm 6 -c tessedit_char_whitelist=0123456789'))
                # ----------------------------------------
                
                # Var 5: Scaled + Inverted (White text on black?)
                inverted = cv2.bitwise_not(thresh)
                variations.append(("Inverted-PSM6", inverted, r'--psm 6 -c tessedit_char_whitelist=0123456789'))
                
                # Var 6: PSM 8 (Treat as single word) - Good for isolated numbers
                variations.append(("Scaled-PSM8", scaled, r'--psm 8 -c tessedit_char_whitelist=0123456789'))
                
                # Var 7: PSM 13 (Raw Line) - Bypasses layout analysis
                variations.append(("Scaled-PSM13", scaled, r'--psm 13 -c tessedit_char_whitelist=0123456789'))

                # Collect all valid candidates
                candidates = []

                # Try all variations
                for name, img_variant, config in variations:
                    ocr_text = pytesseract.image_to_string(img_variant, config=config).strip()
                    digits = re.sub(r'\D', '', ocr_text)
                    
                    logger.info(f"     [OCR-Attempt] Method: {name} | Raw: '{ocr_text}' -> Digits: '{digits}'")
                    
                    # 1. Clean up known noise (leading 2)
                    if len(digits) == 6 and digits.startswith('2'):
                        digits = digits[1:]
                        logger.info(f"       -> [Heuristic] Removed leading 2: Now {digits}")

                    # 2. Strict Length Check
                    if len(digits) >= 4 and len(digits) <= 6:
                         candidates.append((digits, name, img_variant))
                    
                    # 3. Regex Fallback for longer strings
                    if len(digits) > 6:
                        chunks = digits.replace(' ', ',').split(',')
                        for c in chunks:
                             if len(c) in [4,5,6] and c.startswith('1'):
                                 candidates.append((c, f"{name}-Chunk", img_variant))
                        
                        search = re.search(r'\b(1\d{4})\b', digits)
                        if search:
                             candidates.append((search.group(1), f"{name}-Regex", img_variant))

                # Evaluation Strategy: Length 5 > Length 6 > Length 4
                scored_candidates = []
                for val, method, img in candidates:
                    score = 0
                    if len(val) == 5: score += 10
                    if val.startswith('1'): score += 5
                    if method.startswith("Scaled"): score += 2 
                    
                    scored_candidates.append((score, val, method, img))
                
                # Sort descending
                scored_candidates.sort(key=lambda x: x[0], reverse=True)
                
                if scored_candidates:
                    best_score, best_val, best_method, best_img = scored_candidates[0]
                    logger.info(f"   [WINNER]: {best_val} (Score: {best_score} | Method: {best_method})")
                    cv2.imwrite(f"debug_gc_WINNER_rot{rotation}.png", np.array(best_img))
                    return best_val
                else:
                    logger.info("   [Fail] No valid candidates found in any method")

                # Save the raw crop debug if all failed
                cv2.imwrite(f"debug_gc_failed_final_rot{rotation}.png", np.array(roi_pil))

        # Fallback: Fixed Crop (If label failed)
        # Production uses x~2400 for 90/270. 
        # For 180 (Portrait), coordinates would be different if we rely on that.
        # But let's stick to Dynamic Label search as primary.
        if not label_found:
             logger.info(f"   [Skip] Label not found in Rot {rotation}°")

    return None

    return None

def main():
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\ilovepdf_merged (2).pdf"
    
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return
        
    print("=" * 60)
    logger.info("TESTING ENHANCED TESSERACT (NO-AVX SOLUTION)")
    print("=" * 60)
    
    pages = convert_from_path(pdf_path, dpi=300)
    
    for i, page in enumerate(pages, 1):
        print(f"\n[Page] {i}...")
        
        # Try all rotations for type detection
        is_consignment = False
        consignment_rot_found = 0
        
        for rot in [90, 0, 180, 270]:
             check_page = page.rotate(rot, expand=True)
             check_text = pytesseract.image_to_string(check_page, config='--psm 6')
             
             if "CONSIGNMENT" in check_text.upper() and "NOTE" in check_text.upper():
                  is_consignment = True
                  consignment_rot_found = rot
                  break
        
        if is_consignment:
             print(f"   Type: CONSIGNMENT (Detected at {consignment_rot_found}°)")
             
             gc = extract_gc_tesseract_enhanced(page)
             if gc:
                 print(f"   [SUCCESS]: GC Number = {gc}")
             else:
                 print(f"   [FAILED] to extract GC")
        else:
             print("   Type: INVOICE (Skipping)")

if __name__ == "__main__":
    main()
