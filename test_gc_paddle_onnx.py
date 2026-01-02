#!/usr/bin/env python
"""
GC Number Extraction Test Script - Using PaddleOCR with ONNX Runtime (No AVX Required)

This script tests PaddleOCR with ONNX backend for extracting GC numbers.
ONNX Runtime does NOT require AVX/AVX2 and works on most CPUs.

Installation:
    pip install paddleocr onnxruntime
"""

import sys
import os
import re
from typing import Optional, Tuple
import logging

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# PDF to image conversion
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

# PaddleOCR imports
try:
    from paddleocr import PaddleOCR
    import numpy as np
    from PIL import Image
    HAS_PADDLE = True
    logger.info("✓ PaddleOCR available")
except ImportError as e:
    HAS_PADDLE = False
    logger.warning(f"✗ PaddleOCR not available: {e}")
    logger.warning("Install with: pip install paddleocr onnxruntime")


# Initialize PaddleOCR with ONNX (no AVX required)
_paddle_ocr = None


def _get_paddle_ocr():
    """Get or initialize PaddleOCR with ONNX backend (CPU, no AVX)"""
    global _paddle_ocr
    if _paddle_ocr is None:
        logger.info("[PaddleOCR] Loading OCR model with ONNX backend...")
        # use_onnx=True disables MKL-DNN which requires AVX
        # enable_mkldnn=False ensures no AVX usage
        _paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=False,
            use_onnx=True,           # Use ONNX runtime (no AVX)
            enable_mkldnn=False,     # Disable MKL-DNN (requires AVX)
            show_log=False
        )
        logger.info("[PaddleOCR] Model loaded successfully")
    return _paddle_ocr


def _find_gc_label_position(rotated, top_percent=0.50):
    """Find G.C.No label position in top portion of page using Tesseract"""
    
    top_height = int(rotated.height * top_percent)
    top_region = rotated.crop((0, 0, rotated.width, top_height))
    
    data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper().strip()
        
        patterns = [
            r'G\.?C\.?N',
            r'5\.?C\.?N',
            r'6\.?C\.?N',
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


def _extract_gc_with_paddle_onnx(crop_image) -> Optional[str]:
    """Extract GC number using PaddleOCR with ONNX"""
    if not HAS_PADDLE:
        return None
    
    try:
        import cv2
        
        # Convert PIL to numpy
        img_np = np.array(crop_image)
        
        # Convert to grayscale if needed
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # Preprocessing - scale up for better OCR
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Convert back to RGB (PaddleOCR expects 3 channels)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        # Get PaddleOCR model
        ocr = _get_paddle_ocr()
        
        # Run OCR
        result = ocr.ocr(rgb, cls=True)
        
        # Extract text
        all_text = ""
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text, confidence = line[1]
                    all_text += text + " "
                    logger.info(f"[PaddleOCR] Detected: '{text}' (conf: {confidence:.2f})")
        
        logger.info(f"[PaddleOCR] Raw text: {all_text.strip()}")
        
        # Look for 5-digit numbers
        digits = re.sub(r'\D', '', all_text)
        
        if len(digits) == 5:
            logger.info(f"[PaddleOCR] Found GC: {digits}")
            return digits
        
        # Try to find 5-digit pattern starting with 1
        if len(digits) >= 4:
            match = re.search(r'1\d{4}', digits)
            if match:
                logger.info(f"[PaddleOCR] Found GC (1xxxx pattern): {match.group(0)}")
                return match.group(0)
        
        logger.warning(f"[PaddleOCR] No valid GC found in: {digits}")
        
    except Exception as e:
        logger.error(f"[PaddleOCR] Error: {e}")
    
    return None


def extract_gc_with_paddle_onnx(page_image) -> Optional[str]:
    """Main extraction function - tries rotations and finds GC number"""
    
    for rotation in [90, 270]:
        logger.info(f"[PaddleOCR] Trying rotation {rotation}°")
        rotated = page_image.rotate(rotation, expand=True)
        
        # Find G.C.No label position
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"[PaddleOCR] Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']})")
            
            # Crop the number area
            crop_x1 = gc_pos['x'] + gc_pos['w'] - 30
            crop_y1 = gc_pos['y'] - 60
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Save crop for debugging
            crop.save(f"gc_crop_paddle_{rotation}.png")
            
            # Use PaddleOCR
            gc_num = _extract_gc_with_paddle_onnx(crop)
            if gc_num:
                return gc_num
        else:
            # Fallback: use fixed position
            logger.info(f"[PaddleOCR] Label not found at {rotation}°, trying fixed position")
            crop = rotated.crop((2400, 450, 3509, 850))
            
            gc_num = _extract_gc_with_paddle_onnx(crop)
            if gc_num:
                return gc_num
    
    return None


def test_on_pdfs():
    """Test PaddleOCR ONNX GC extraction on Format 3 PDFs"""
    
    if not HAS_PADDLE:
        print("\n❌ PaddleOCR is not installed. Install with: pip install paddleocr onnxruntime")
        return
    
    uploads_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads"
    
    format3_pdfs = [
        "DocScanner 23-Dec-2025 05-02 PM.pdf",
        "DocScanner 23-Dec-2025 05-02 PM-1-2 (1).pdf",
    ]
    
    print("\n" + "=" * 70)
    print("Testing PaddleOCR (ONNX) for GC Number Extraction")
    print("=" * 70)
    
    results = []
    
    for pdf_name in format3_pdfs:
        pdf_path = os.path.join(uploads_dir, pdf_name)
        
        if not os.path.exists(pdf_path):
            print(f"\n⚠ PDF not found: {pdf_name}")
            continue
        
        print(f"\n📄 Processing: {pdf_name}")
        
        try:
            pages = convert_from_path(pdf_path, dpi=300)
            
            for page_num, page in enumerate(pages, 1):
                text_90 = pytesseract.image_to_string(page.rotate(90, expand=True), config='--psm 6')
                text_270 = pytesseract.image_to_string(page.rotate(270, expand=True), config='--psm 6')
                
                is_consignment = 'CONSIGNMENT' in text_90.upper() or 'CONSIGNMENT' in text_270.upper()
                
                if is_consignment:
                    print(f"  Page {page_num}: CONSIGNMENT page detected")
                    
                    gc_number = extract_gc_with_paddle_onnx(page)
                    
                    if gc_number:
                        print(f"    ✓ GC Number: {gc_number}")
                        results.append((pdf_name, page_num, gc_number, "success"))
                    else:
                        print(f"    ✗ GC Number: NOT FOUND")
                        results.append((pdf_name, page_num, None, "not_found"))
                else:
                    print(f"  Page {page_num}: INVOICE page (skipping)")
                    
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append((pdf_name, 0, None, f"error: {e}"))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    success = len([r for r in results if r[3] == "success"])
    not_found = len([r for r in results if r[3] == "not_found"])
    errors = len([r for r in results if r[3].startswith("error")])
    
    print(f"Total consignment pages tested: {len(results)}")
    print(f"  ✓ GC found: {success}")
    print(f"  ✗ GC not found: {not_found}")
    print(f"  ⚠ Errors: {errors}")


if __name__ == "__main__":
    test_on_pdfs()
