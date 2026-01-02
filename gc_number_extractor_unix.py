"""
GC Number Extractor - Using EasyOCR for tilted text handling
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import easyocr
import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Initialize EasyOCR reader once
_easyocr_reader = None

def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easyocr_reader


def _is_consignment_page(text: str) -> bool:
    if not text:
        return False
    return 'CONSIGNMENT' in text.upper() and 'NOTE' in text.upper()


def _find_gc_label_position(rotated, top_percent=0.50):
    """Find G.C.No label position in top portion of page"""
    
    top_height = int(rotated.height * top_percent)
    top_region = rotated.crop((0, 0, rotated.width, top_height))
    
    data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper().strip()
        
        # Various G.C.No patterns including OCR errors
        patterns = [
            r'G\.?C\.?N',      # G.C.No, GCNo, G.CN
            r'5\.?C\.?N',      # 5.C.N (G misread as 5)
            r'6\.?C\.?N',      # 6.C.N (G misread as 6)
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


def _extract_gc_with_tesseract(crop_image) -> Optional[str]:
    """Fallback: Extract GC number using Tesseract when EasyOCR fails"""
    import numpy as np
    import cv2
    from PIL import Image
    
    try:
        # Convert PIL to numpy for OpenCV processing
        img_np = np.array(crop_image)
        
        # Convert to grayscale if needed
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # Preprocessing for better OCR
        # Scale up
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR with digit-focused config
        text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789')
        
        # Extract 5-digit number
        digits = re.sub(r'\D', '', text)
        
        if len(digits) == 5:
            logger.info(f"[GC] Tesseract fallback found: {digits}")
            return digits
        
        # Try to find 5-digit pattern starting with 1
        if len(digits) >= 4:
            match = re.search(r'1\d{4}', digits)
            if match:
                logger.info(f"[GC] Tesseract fallback found: {match.group(0)}")
                return match.group(0)
        
    except Exception as e:
        logger.warning(f"[GC] Tesseract fallback failed: {e}")
    
    return None


def _extract_gc_with_easyocr(crop_image) -> Optional[str]:
    """Extract GC number using EasyOCR with Tesseract fallback for server compatibility"""
    import numpy as np
    from PIL import Image
    
    # Try EasyOCR first
    try:
        reader = _get_easyocr_reader()
        
        # Convert PIL to numpy
        img_np = np.array(crop_image)
        
        results = reader.readtext(img_np)
        
        for detection in results:
            bbox, text, conf = detection
            
            # Look for 5-digit numbers with high confidence
            digits = re.sub(r'\D', '', text)
            
            if len(digits) == 5 and conf > 0.5:
                return digits
            
            # Also accept 4-6 digit numbers with 1 prefix
            if len(digits) >= 4 and conf > 0.5:
                match = re.search(r'1\d{4}', digits)
                if match:
                    return match.group(0)
                    
    except RuntimeError as e:
        # Handle "could not create a primitive" error on servers without AVX support
        error_msg = str(e).lower()
        if 'primitive' in error_msg or 'mkl' in error_msg or 'onednn' in error_msg:
            logger.warning(f"[GC] EasyOCR failed (CPU compatibility issue), using Tesseract fallback")
            return _extract_gc_with_tesseract(crop_image)
        else:
            logger.warning(f"[GC] EasyOCR RuntimeError: {e}, using Tesseract fallback")
            return _extract_gc_with_tesseract(crop_image)
    except Exception as e:
        logger.warning(f"[GC] EasyOCR failed: {e}, using Tesseract fallback")
        return _extract_gc_with_tesseract(crop_image)
    
    # If EasyOCR found nothing, try Tesseract as fallback
    return _extract_gc_with_tesseract(crop_image)


def extract_gc_number_from_pdf_page(page_image) -> Optional[str]:
    """Extract GC Number using EasyOCR"""
    
    for rotation in [90, 270]:
        rotated = page_image.rotate(rotation, expand=True)
        
        # Find G.C.No label position
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"[GC] Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']})")
            
            # Crop the number area
            crop_x1 = gc_pos['x'] + gc_pos['w'] - 30
            crop_y1 = gc_pos['y'] - 60
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Use EasyOCR
            gc_num = _extract_gc_with_easyocr(crop)
            if gc_num:
                logger.info(f"[GC] EasyOCR: {gc_num}")
                return gc_num
        else:
            # Fallback: use fixed position if label not found
            # G.C.No is typically at x~2500, y~600 for 300 DPI
            crop = rotated.crop((2400, 450, 3509, 850))  # Full width to right edge
            gc_num = _extract_gc_with_easyocr(crop)
            if gc_num:
                logger.info(f"[GC] EasyOCR (fixed pos): {gc_num}")
                return gc_num
    
    return None


def extract_page_type_and_gc(page_image) -> Tuple[str, Optional[str]]:
    for rotation in [90, 270]:
        rotated = page_image.rotate(rotation, expand=True)
        text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
        
        if _is_consignment_page(text):
            gc_num = extract_gc_number_from_pdf_page(page_image)
            return ("CONSIGNMENT", gc_num)
    
    return ("OTHER", None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    
    print("=" * 60)
    print("GC EXTRACTION - EasyOCR")
    print("=" * 60)
    
    pages = convert_from_path(pdf_path, dpi=300)
    
    print(f"{'Page':<6} {'Type':<15} {'GC Number':<15}")
    print("-" * 40)
    
    consignment_count = 0
    gc_found_count = 0
    
    for i, page in enumerate(pages, 1):
        page_type, gc_num = extract_page_type_and_gc(page)
        
        if page_type == "CONSIGNMENT":
            consignment_count += 1
            if gc_num:
                gc_found_count += 1
            print(f"{i:<6} {'CONSIGNMENT':<15} {gc_num or '-':<15}")
        else:
            print(f"{i:<6} {'OTHER':<15} {'-':<15}")
    
    print("-" * 40)
    print(f"Consignment Pages: {consignment_count}")
    print(f"GC Numbers Found: {gc_found_count}/{consignment_count}")
    print(f"Success Rate: {100*gc_found_count/max(consignment_count,1):.0f}%")
    print("=" * 60)
