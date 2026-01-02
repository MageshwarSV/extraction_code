"""
GC Number Extractor - Using RapidOCR ONNX (NO AVX REQUIRED)

This module extracts GC numbers from consignment pages.
Uses RapidOCR with ONNX Runtime which works on CPUs without AVX/AVX2 support.

Installation:
    pip install rapidocr-onnxruntime
"""
import sys
import os
import re
from typing import Optional, Tuple
import logging

# Handle different path setups
if os.name == 'nt':  # Windows
    sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
else:  # Linux
    sys.path.insert(0, '/root/wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Initialize RapidOCR once
_rapidocr_reader = None

def _get_rapidocr_reader():
    """Get or initialize RapidOCR with ONNX backend (NO AVX REQUIRED)"""
    global _rapidocr_reader
    if _rapidocr_reader is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapidocr_reader = RapidOCR()
            logger.info("[GC] RapidOCR ONNX initialized successfully")
        except ImportError:
            logger.warning("[GC] RapidOCR not available, will use Tesseract fallback")
            _rapidocr_reader = None
    return _rapidocr_reader


def _is_consignment_page(text: str) -> bool:
    """Check if text indicates a consignment page"""
    if not text:
        return False
    return 'CONSIGNMENT' in text.upper() and 'NOTE' in text.upper()


def _find_gc_label_position(rotated, top_percent=0.50):
    """Find G.C.No label position in top portion of page using Tesseract"""
    
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
    """Fallback: Extract GC number using Tesseract when RapidOCR fails"""
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


def _extract_gc_with_rapidocr(crop_image) -> Optional[str]:
    """Extract GC number using RapidOCR ONNX (NO AVX REQUIRED)"""
    from PIL import Image
    
    # Try RapidOCR first
    try:
        reader = _get_rapidocr_reader()
        
        if reader is None:
            # RapidOCR not available, use Tesseract
            return _extract_gc_with_tesseract(crop_image)
        
        # Convert PIL to numpy
        img_np = np.array(crop_image)
        
        # Convert to grayscale if needed
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # Preprocessing - scale up for better OCR
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Convert back to RGB (RapidOCR expects 3 channels)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        # Run OCR
        result, elapse = reader(rgb)
        
        # Extract text
        all_text = ""
        if result:
            for line in result:
                if len(line) >= 2:
                    text = line[1]
                    conf = float(line[2]) if len(line) > 2 else 0
                    all_text += text + " "
                    logger.debug(f"[GC] RapidOCR detected: '{text}' (conf: {conf:.2f})")
        
        # Look for 5-digit numbers
        digits = re.sub(r'\D', '', all_text)
        
        if len(digits) == 5:
            logger.info(f"[GC] RapidOCR found: {digits}")
            return digits
        
        # Try to find 5-digit pattern starting with 1
        if len(digits) >= 4:
            match = re.search(r'1\d{4}', digits)
            if match:
                logger.info(f"[GC] RapidOCR found (1xxxx pattern): {match.group(0)}")
                return match.group(0)
        
        logger.debug(f"[GC] RapidOCR no valid GC in: {digits}")
                    
    except Exception as e:
        logger.warning(f"[GC] RapidOCR failed: {e}, using Tesseract fallback")
        return _extract_gc_with_tesseract(crop_image)
    
    # If RapidOCR found nothing, try Tesseract as fallback
    return _extract_gc_with_tesseract(crop_image)


def extract_gc_number_from_pdf_page(page_image) -> Optional[str]:
    """
    Extract GC Number using RapidOCR ONNX (NO AVX REQUIRED)
    
    Tries rotations in order: 90° → 180° → 270° → 0°
    Uses Tesseract to pre-check if CONSIGNMENT is visible at each rotation.
    """
    
    # Rotation order: 90° first (most common), then 180°, 270°, 0°
    rotation_order = [90, 180, 270, 0]
    
    for rotation in rotation_order:
        logger.debug(f"[GC] Trying rotation {rotation}°")
        
        if rotation == 0:
            rotated = page_image
        else:
            rotated = page_image.rotate(rotation, expand=True)
        
        # Pre-check with Tesseract: is this a CONSIGNMENT page at this rotation?
        try:
            text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
            is_consignment = _is_consignment_page(text)
        except:
            is_consignment = False
        
        if not is_consignment:
            logger.debug(f"[GC] No CONSIGNMENT found at rotation {rotation}°, skipping...")
            continue
        
        logger.info(f"[GC] ✓ CONSIGNMENT found at rotation {rotation}°")
        
        # Find G.C.No label position
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"[GC] Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']})")
            
            # Crop the number area (with bounds checking)
            crop_x1 = max(0, gc_pos['x'] + gc_pos['w'] - 30)
            crop_y1 = max(0, gc_pos['y'] - 60)
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = min(top_region.height, gc_pos['y'] + gc_pos['h'] + 80)
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Use RapidOCR
            gc_num = _extract_gc_with_rapidocr(crop)
            if gc_num:
                logger.info(f"[GC] ✓ GC Number found at rotation {rotation}°: {gc_num}")
                return gc_num
        else:
            # Fallback: use fixed position if label not found
            logger.debug(f"[GC] Label not found at {rotation}°, trying fixed position")
            try:
                crop = rotated.crop((2400, 450, 3509, 850))
                gc_num = _extract_gc_with_rapidocr(crop)
                if gc_num:
                    logger.info(f"[GC] ✓ GC Number found at fixed position, rotation {rotation}°: {gc_num}")
                    return gc_num
            except Exception as e:
                logger.debug(f"[GC] Fixed position crop failed: {e}")
    
    return None


def extract_page_type_and_gc(page_image) -> Tuple[str, Optional[str]]:
    """Detect page type and extract GC number if consignment"""
    
    # Check all 4 rotations for CONSIGNMENT
    for rotation in [0, 90, 180, 270]:
        if rotation == 0:
            rotated = page_image
        else:
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
    print("GC EXTRACTION - RapidOCR ONNX (NO AVX REQUIRED)")
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
