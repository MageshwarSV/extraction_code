"""
END-TO-END TEST: PDF -> GC Number Extraction
Uses the proven formula:
1. Rotate + find label + crop
2. BGR adjust (B+23, G-19, R-49)
3. Grayscale + Scale 2x
4. Fixed threshold 126
5. OCR PSM 6
"""
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
from PIL import Image, ImageOps
import re
import os

PDF_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\ilovepdf_merged (2).pdf"
THRESHOLD_VALUE = 126

def is_consignment_page(page_pil, rotation):
    """Check if page is a consignment note at given rotation"""
    rotated = page_pil.rotate(rotation, expand=True)
    text = pytesseract.image_to_string(rotated, config='--psm 6')
    return 'CONSIGNMENT' in text.upper() and 'NOTE' in text.upper()

def find_and_crop_gc(page_pil):
    """Find G.C.No label and crop the number region"""
    for rotation in [180, 90, 270, 0]:
        rotated = page_pil.rotate(rotation, expand=True)
        
        # Scan top 50%
        top_h = int(rotated.height * 0.5)
        top_region = rotated.crop((0, 0, rotated.width, top_h))
        
        # OCR to find label
        data = pytesseract.image_to_data(top_region, config='--psm 6', output_type=Output.DICT)
        
        for i, text in enumerate(data['text']):
            if not text:
                continue
            
            # Check for G.C.No pattern
            if re.search(r'(G\.?C\.?N|5\.?C\.?N|6\.?C\.?N|G\.?C\.?No|GC\s*No)', text, re.IGNORECASE):
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # Crop region (to the RIGHT of the label)
                crop_x1 = x + w + 5
                crop_y1 = max(0, y - 60)
                crop_x2 = min(top_region.width, x + w + 700)
                crop_y2 = y + h + 80
                
                roi = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                roi = ImageOps.expand(roi, border=20, fill='white')
                
                return roi, rotation
    
    return None, None

def extract_gc_number(crop_pil):
    """Extract GC number from cropped image using proven method"""
    # Convert PIL to OpenCV
    img = np.array(crop_pil)
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    print(f"  Crop BGR mean: B={np.mean(img[:,:,0]):.1f}, G={np.mean(img[:,:,1]):.1f}, R={np.mean(img[:,:,2]):.1f}")
    
    # Step 1: BGR adjustment (pink -> purple)
    adjusted = img.copy().astype(np.float32)
    adjusted[:,:,0] = np.clip(adjusted[:,:,0] + 23, 0, 255)  # B +23
    adjusted[:,:,1] = np.clip(adjusted[:,:,1] - 19, 0, 255)  # G -19
    adjusted[:,:,2] = np.clip(adjusted[:,:,2] - 49, 0, 255)  # R -49
    adjusted = adjusted.astype(np.uint8)
    
    # CRITICAL: Save and reload to avoid float rounding issues
    cv2.imwrite("gc_test_adjusted.png", adjusted)
    adjusted = cv2.imread("gc_test_adjusted.png")
    
    # Step 2: Grayscale
    gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
    print(f"  Gray mean: {np.mean(gray):.1f}")
    
    # Step 3: Scale 2x
    scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # Step 4: Fixed threshold 126
    _, thresh = cv2.threshold(scaled, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
    
    # Save for debug
    cv2.imwrite("gc_test_result.png", thresh)
    
    # Step 5: OCR with PSM 6
    config = '--psm 6 -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  OCR: '{raw}' -> '{digits}'")
    
    if len(digits) == 5:
        return digits
    
    # Try to find 1xxxx pattern
    if len(digits) >= 4:
        match = re.search(r'1\d{4}', digits)
        if match:
            return match.group(0)
    
    return None

def main():
    print("=" * 60)
    print("END-TO-END GC EXTRACTION TEST")
    print(f"PDF: {os.path.basename(PDF_PATH)}")
    print("=" * 60)
    
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        return
    
    pages = convert_from_path(PDF_PATH, dpi=300)
    print(f"Loaded {len(pages)} pages\n")
    
    for i, page in enumerate(pages, 1):
        print(f"--- Page {i} ---")
        
        # Check if consignment
        is_consignment = False
        consignment_rotation = None
        for rot in [180, 90, 270, 0]:
            if is_consignment_page(page, rot):
                is_consignment = True
                consignment_rotation = rot
                break
        
        if not is_consignment:
            print("  Type: INVOICE (Skipping)")
            continue
        
        print(f"  Type: CONSIGNMENT (at {consignment_rotation} deg)")
        
        # Find and crop GC region
        crop, rotation = find_and_crop_gc(page)
        
        if crop is None:
            print("  [FAILED] Could not find G.C.No label")
            continue
        
        print(f"  Label found at rotation {rotation}")
        crop.save("gc_test_crop.png")
        
        # Extract GC number
        gc_number = extract_gc_number(crop)
        
        if gc_number:
            print(f"  [SUCCESS] GC Number: {gc_number}")
            if gc_number == "14549":
                print("  [CORRECT] Matches expected value!")
        else:
            print("  [FAILED] Could not extract GC number")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
