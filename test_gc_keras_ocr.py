#!/usr/bin/env python
"""
GC Number Extraction Test Script - Using Keras-OCR

Keras-OCR uses TensorFlow backend which can run on CPU without AVX.

Installation:
    pip install keras-ocr tensorflow-cpu
"""

import sys
import os
import re
from typing import Optional
import logging

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# PDF to image conversion
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

# Keras-OCR imports
try:
    import keras_ocr
    import numpy as np
    from PIL import Image
    HAS_KERAS_OCR = True
    logger.info("✓ Keras-OCR available")
except ImportError as e:
    HAS_KERAS_OCR = False
    logger.warning(f"✗ Keras-OCR not available: {e}")
    logger.warning("Install with: pip install keras-ocr tensorflow-cpu")


# Initialize Keras-OCR pipeline once
_keras_pipeline = None


def _get_keras_pipeline():
    """Get or initialize Keras-OCR pipeline"""
    global _keras_pipeline
    if _keras_pipeline is None:
        logger.info("[Keras-OCR] Loading pipeline (first time may take a moment)...")
        _keras_pipeline = keras_ocr.pipeline.Pipeline()
        logger.info("[Keras-OCR] Pipeline loaded successfully")
    return _keras_pipeline


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


def _extract_gc_with_keras_ocr(crop_image) -> Optional[str]:
    """Extract GC number using Keras-OCR"""
    if not HAS_KERAS_OCR:
        return None
    
    try:
        import cv2
        
        # Convert PIL to numpy
        if isinstance(crop_image, Image.Image):
            img_np = np.array(crop_image)
        else:
            img_np = crop_image
        
        # Convert to RGB if needed
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
        elif img_np.shape[2] == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
        
        # Scale up for better OCR
        img_np = cv2.resize(img_np, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Get Keras-OCR pipeline
        pipeline = _get_keras_pipeline()
        
        # Run OCR
        results = pipeline.recognize([img_np])
        
        # Extract text
        all_text = ""
        if results and results[0]:
            for text, box in results[0]:
                all_text += text + " "
                logger.info(f"[Keras-OCR] Detected: '{text}'")
        
        logger.info(f"[Keras-OCR] Raw text: {all_text.strip()}")
        
        # Look for 5-digit numbers
        digits = re.sub(r'\D', '', all_text)
        
        if len(digits) == 5:
            logger.info(f"[Keras-OCR] Found GC: {digits}")
            return digits
        
        # Try to find 5-digit pattern starting with 1
        if len(digits) >= 4:
            match = re.search(r'1\d{4}', digits)
            if match:
                logger.info(f"[Keras-OCR] Found GC (1xxxx pattern): {match.group(0)}")
                return match.group(0)
        
        logger.warning(f"[Keras-OCR] No valid GC found in: {digits}")
        
    except Exception as e:
        logger.error(f"[Keras-OCR] Error: {e}")
    
    return None


def extract_gc_with_keras_ocr(page_image) -> Optional[str]:
    """Main extraction function - tries rotations and finds GC number"""
    
    for rotation in [90, 270]:
        logger.info(f"[Keras-OCR] Trying rotation {rotation}°")
        rotated = page_image.rotate(rotation, expand=True)
        
        # Find G.C.No label position
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"[Keras-OCR] Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']})")
            
            # Crop the number area
            crop_x1 = gc_pos['x'] + gc_pos['w'] - 30
            crop_y1 = gc_pos['y'] - 60
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Save crop for debugging
            crop.save(f"gc_crop_keras_{rotation}.png")
            
            # Use Keras-OCR
            gc_num = _extract_gc_with_keras_ocr(crop)
            if gc_num:
                return gc_num
        else:
            # Fallback: use fixed position
            logger.info(f"[Keras-OCR] Label not found at {rotation}°, trying fixed position")
            crop = rotated.crop((2400, 450, 3509, 850))
            
            gc_num = _extract_gc_with_keras_ocr(crop)
            if gc_num:
                return gc_num
    
    return None


def test_on_pdfs():
    """Test Keras-OCR GC extraction on Format 3 PDFs"""
    
    if not HAS_KERAS_OCR:
        print("\n❌ Keras-OCR is not installed. Install with: pip install keras-ocr tensorflow-cpu")
        return
    
    uploads_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads"
    
    format3_pdfs = [
        "DocScanner 23-Dec-2025 05-02 PM.pdf",
        "DocScanner 23-Dec-2025 05-02 PM-1-2 (1).pdf",
    ]
    
    print("\n" + "=" * 70)
    print("Testing Keras-OCR for GC Number Extraction")
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
                    
                    gc_number = extract_gc_with_keras_ocr(page)
                    
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
