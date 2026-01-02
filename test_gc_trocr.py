#!/usr/bin/env python
"""
GC Number Extraction Test Script - Using TrOCR (Hugging Face Transformers)

TrOCR is a transformer-based OCR model that works on ANY CPU (no AVX required).
It uses pure Python/PyTorch operations.

Installation:
    pip install transformers pillow torch
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

# TrOCR imports
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from PIL import Image
    import numpy as np
    HAS_TROCR = True
    logger.info("✓ TrOCR (transformers) available")
except ImportError as e:
    HAS_TROCR = False
    logger.warning(f"✗ TrOCR not available: {e}")
    logger.warning("Install with: pip install transformers pillow torch")


# Initialize TrOCR model once
_trocr_processor = None
_trocr_model = None


def _get_trocr_model():
    """Get or initialize TrOCR model"""
    global _trocr_processor, _trocr_model
    if _trocr_model is None:
        logger.info("[TrOCR] Loading model (first time may take a moment)...")
        # Use the small printed model for efficiency
        _trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-small-printed')
        _trocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-small-printed')
        logger.info("[TrOCR] Model loaded successfully")
    return _trocr_processor, _trocr_model


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


def _extract_gc_with_trocr(crop_image) -> Optional[str]:
    """Extract GC number using TrOCR"""
    if not HAS_TROCR:
        return None
    
    try:
        import cv2
        
        # Convert to PIL if numpy
        if isinstance(crop_image, np.ndarray):
            crop_pil = Image.fromarray(crop_image)
        else:
            crop_pil = crop_image
        
        # Convert to RGB
        if crop_pil.mode != 'RGB':
            crop_pil = crop_pil.convert('RGB')
        
        # Resize for TrOCR (it works better with reasonably sized images)
        # TrOCR expects 384x384 but can handle larger
        w, h = crop_pil.size
        if w > 384 or h > 384:
            scale = min(384 / w, 384 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            crop_pil = crop_pil.resize((new_w, new_h), Image.LANCZOS)
        
        # Get TrOCR model
        processor, model = _get_trocr_model()
        
        # Process image
        pixel_values = processor(images=crop_pil, return_tensors="pt").pixel_values
        
        # Generate text
        generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        logger.info(f"[TrOCR] Raw text: {text}")
        
        # Look for 5-digit numbers
        digits = re.sub(r'\D', '', text)
        
        if len(digits) == 5:
            logger.info(f"[TrOCR] Found GC: {digits}")
            return digits
        
        # Try to find 5-digit pattern starting with 1
        if len(digits) >= 4:
            match = re.search(r'1\d{4}', digits)
            if match:
                logger.info(f"[TrOCR] Found GC (1xxxx pattern): {match.group(0)}")
                return match.group(0)
        
        logger.warning(f"[TrOCR] No valid GC found in: {digits}")
        
    except Exception as e:
        logger.error(f"[TrOCR] Error: {e}")
    
    return None


def extract_gc_with_trocr(page_image) -> Optional[str]:
    """Main extraction function - tries rotations and finds GC number"""
    
    for rotation in [90, 270]:
        logger.info(f"[TrOCR] Trying rotation {rotation}°")
        rotated = page_image.rotate(rotation, expand=True)
        
        # Find G.C.No label position
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"[TrOCR] Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']})")
            
            # Crop the number area
            crop_x1 = gc_pos['x'] + gc_pos['w'] - 30
            crop_y1 = gc_pos['y'] - 60
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Save crop for debugging
            crop.save(f"gc_crop_trocr_{rotation}.png")
            
            # Use TrOCR
            gc_num = _extract_gc_with_trocr(crop)
            if gc_num:
                return gc_num
        else:
            # Fallback: use fixed position
            logger.info(f"[TrOCR] Label not found at {rotation}°, trying fixed position")
            crop = rotated.crop((2400, 450, 3509, 850))
            
            gc_num = _extract_gc_with_trocr(crop)
            if gc_num:
                return gc_num
    
    return None


def test_on_pdfs():
    """Test TrOCR GC extraction on Format 3 PDFs"""
    
    if not HAS_TROCR:
        print("\n❌ TrOCR is not installed. Install with: pip install transformers pillow torch")
        return
    
    uploads_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads"
    
    format3_pdfs = [
        "DocScanner 23-Dec-2025 05-02 PM.pdf",
        "DocScanner 23-Dec-2025 05-02 PM-1-2 (1).pdf",
    ]
    
    print("\n" + "=" * 70)
    print("Testing TrOCR (Hugging Face) for GC Number Extraction")
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
                    
                    gc_number = extract_gc_with_trocr(page)
                    
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
