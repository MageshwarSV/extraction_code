
"""
Standalone script to test GC Number extraction using RapidOCR (CPU-friendly).
Usage: python test_rapidocr_gc_v2.py
"""
import sys
import os
import re
import logging
import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.getcwd())

# Try to import RapidOCR
try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPIDOCR = True
    processed = "rapidocr"
except ImportError:
    HAS_RAPIDOCR = False
    logger.error("❌ RapidOCR not found! Please run: pip install rapidocr_onnxruntime")
    # sys.exit(1) # Don't exit, just let it fail gracefully later

# Initialize RapidOCR engine
_rapid_ocr = None

def get_rapid_ocr():
    global _rapid_ocr
    if _rapid_ocr is None and HAS_RAPIDOCR:
        # det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False for CPU
        _rapid_ocr = RapidOCR() 
    return _rapid_ocr

def _is_consignment_page(text: str) -> bool:
    if not text:
        return False
    return 'CONSIGNMENT' in text.upper() and 'NOTE' in text.upper()

def _find_gc_label_position(rotated, top_percent=0.50):
    """Find G.C.No label using Tesseract (fast) to locate the crop region"""
    top_height = int(rotated.height * top_percent)
    top_region = rotated.crop((0, 0, rotated.width, top_height))
    
    data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    for i, word in enumerate(data['text']):
        if not word: continue
        word_upper = word.upper().strip()
        
        patterns = [
            r'G\.?C\.?N', r'5\.?C\.?N', r'6\.?C\.?N'
        ]
        
        for pattern in patterns:
            if re.search(pattern, word_upper):
                return {
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i],
                    'word': word
                }, top_region
    return None, top_region

def _extract_gc_with_rapidocr(crop_image) -> str:
    """Extract GC number using RapidOCR"""
    if not HAS_RAPIDOCR:
        return None
        
    try:
        engine = get_rapid_ocr()
        
        # Convert PIL to numpy (RGB)
        img_np = np.array(crop_image)
        # RapidOCR expects BGR usually if reading via cv2, but RGB is often fine. 
        # Best to follow standard:
        # img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Run inference
        # Returns list of results: [[box], text, confidence]
        result, _ = engine(img_np)
        
        if not result:
            return None
            
        # Parse results
        for item in result:
            text = item[1]
            conf = item[2]
            
            # Look for 5-digit number
            digits = re.sub(r'\D', '', text)
            
            if len(digits) == 5 and conf > 0.4:
                logger.info(f"   [RapidOCR] Found 5-digit: {digits} (conf={conf:.2f}, raw='{text}')")
                return digits
            
            # Also accept 4-6 digit numbers with 1 prefix
            if len(digits) >= 4 and conf > 0.4:
                match = re.search(r'1\d{4}', digits)
                if match:
                    logger.info(f"   [RapidOCR] Found 1xxxx pattern: {match.group(0)} (conf={conf:.2f})")
                    return match.group(0)
                    
    except Exception as e:
        logger.error(f"   [RapidOCR] Error: {e}")
    
    return None

def extract_gc_number_rapid(page_image):
    """Main extraction logic using RapidOCR"""
    
    # Try all rotations (0, 90, 180, 270) to be robust
    for rotation in [90, 0, 270, 180]:
        rotated = page_image.rotate(rotation, expand=True)
        
        # 1. Locate Label
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"✅ Found Label '{gc_pos['word']}' at Rot {rotation}°")
            
            # Crop area around label
            crop_x1 = gc_pos['x'] + gc_pos['w'] - 30
            crop_y1 = gc_pos['y'] - 60
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # 2. Extract with RapidOCR
            gc = _extract_gc_with_rapidocr(crop)
            if gc:
                return gc, rotation
        else:
            # Fallback: Fixed position crop
            logger.info(f"⚠️ Label not found at {rotation}°, trying fixed crop")
            # G.C.No is typically at x~2400, y~450 (for 300 DPI)
            if rotation == 90: # Only try fixed crop on standard side-ways rotation
                 crop = rotated.crop((2400, 450, 3509, 850))
                 gc = _extract_gc_with_rapidocr(crop)
                 if gc:
                     return gc, rotation

    return None, None

def main():
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\ilovepdf_merged (2).pdf"
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found at: {pdf_path}")
        return

    print("=" * 60)
    print(f"TESTING RAPIDOCR on: {os.path.basename(pdf_path)}")
    print("=" * 60)

    if not HAS_RAPIDOCR:
        print("❌ CRITICAL: rapidocr_onnxruntime is NOT installed.")
        print("   Please run: pip install rapidocr_onnxruntime")
        print("   Then run this script again.")
        return

    pages = convert_from_path(pdf_path, dpi=300)
    print(f"Loaded {len(pages)} pages.")
    
    consignment_count = 0
    
    for i, page in enumerate(pages, 1):
        print(f"\n--- Checking Page {i} ---")
        
        # Try all rotations for type detection
        is_consignment = False
        detected_rot = 0
        
        for rot in [90, 0, 180, 270]:
            chk_page = page.rotate(rot, expand=True)
            text = pytesseract.image_to_string(chk_page, config='--psm 6')
            
            if _is_consignment_page(text):
                is_consignment = True
                detected_rot = rot
                print(f"   [Type] Detected CONSIGNMENT at rotation {rot}°")
                break
        
        if is_consignment:
            consignment_count += 1
            
            # Use the page at the detected rotation (or try standard ones)
            # The extraction logic itself tries specific rotations, but let's pass the original page
            # extract_gc_number_rapid handles its own rotation checks (90, 270)
            
            gc_num, gc_rot = extract_gc_number_rapid(page)
            if gc_num:
                print(f"   🎯 GC NUMBER FOUND: {gc_num}")
            else:
                print(f"   ❌ GC NUMBER NOT FOUND (RapidOCR failed)")
        else:
            print(f"   [Type] INVOICE (or undetected) - Skipping")

    print("\n" + "=" * 60)
    print(f"Total Consignment Pages: {consignment_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
