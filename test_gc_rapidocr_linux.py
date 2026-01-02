#!/usr/bin/env python
"""
GC Number Extraction Test Script - Using RapidOCR ONNX (NO AVX REQUIRED)
Linux Server Version

RapidOCR with ONNX Runtime does NOT require AVX - it falls back to SSE instructions.
This makes it compatible with older CPUs.

Installation:
    pip install rapidocr-onnxruntime
"""

import sys
import os
import re
from typing import Optional
import logging

# Linux paths
UPLOADS_DIR = "/root/wbai_doc_extractor_engine-maincopy/uploads"
OUTPUT_FILE = "/root/wbai_doc_extractor_engine-maincopy/uploads/gc_rapidocr_results.txt"
CROP_DIR = "/root/wbai_doc_extractor_engine-maincopy/uploads"

sys.path.insert(0, '/root/wbai_doc_extractor_engine-maincopy')

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# PDF to image conversion
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

# RapidOCR imports
try:
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np
    from PIL import Image
    HAS_RAPIDOCR = True
    logger.info("✓ RapidOCR ONNX available")
except ImportError as e:
    HAS_RAPIDOCR = False
    logger.warning(f"✗ RapidOCR not available: {e}")
    logger.warning("Install with: pip install rapidocr-onnxruntime")


# Initialize RapidOCR once
_rapid_ocr = None


def _get_rapid_ocr():
    """Get or initialize RapidOCR with ONNX backend"""
    global _rapid_ocr
    if _rapid_ocr is None:
        logger.info("[RapidOCR] Loading OCR model...")
        _rapid_ocr = RapidOCR()
        logger.info("[RapidOCR] Model loaded successfully")
    return _rapid_ocr


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


def _extract_gc_with_rapidocr(crop_image, pdf_name="", page_num=0, rotation=0) -> Optional[str]:
    """Extract GC number using RapidOCR ONNX"""
    if not HAS_RAPIDOCR:
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
        
        # Convert back to RGB (RapidOCR expects 3 channels)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        # Get RapidOCR
        ocr = _get_rapid_ocr()
        
        # Run OCR
        result, elapse = ocr(rgb)
        
        # Extract text
        all_text = ""
        if result:
            for line in result:
                # RapidOCR returns: [box, text, confidence]
                if len(line) >= 2:
                    text = line[1]
                    conf = float(line[2]) if len(line) > 2 else 0
                    all_text += text + " "
                    logger.info(f"[RapidOCR] Detected: '{text}' (conf: {conf:.2f})")
        
        logger.info(f"[RapidOCR] Raw text: {all_text.strip()}")
        
        # Look for 5-digit numbers
        digits = re.sub(r'\D', '', all_text)
        
        if len(digits) == 5:
            logger.info(f"[RapidOCR] Found GC: {digits}")
            return digits
        
        # Try to find 5-digit pattern starting with 1
        if len(digits) >= 4:
            match = re.search(r'1\d{4}', digits)
            if match:
                logger.info(f"[RapidOCR] Found GC (1xxxx pattern): {match.group(0)}")
                return match.group(0)
        
        logger.warning(f"[RapidOCR] No valid GC found in: {digits}")
        
    except Exception as e:
        logger.error(f"[RapidOCR] Error: {e}")
    
    return None


def extract_gc_with_rapidocr(page_image, pdf_name="", page_num=0) -> Optional[str]:
    """
    Main extraction function - tries rotations in order: 90° → 180° → 270° → 0°
    
    Logic:
    1. Try rotation 90° first
    2. Use Tesseract to pre-check if "CONSIGNMENT" is in the page
    3. If found, extract GC number with RapidOCR
    4. If not found or GC not extracted, try next rotation
    """
    
    # Rotation order: 90° first (most common), then 180°, 270°, 0°
    rotation_order = [90, 180, 270, 0]
    
    for rotation in rotation_order:
        logger.info(f"[RapidOCR] Trying rotation {rotation}°")
        
        if rotation == 0:
            rotated = page_image
        else:
            rotated = page_image.rotate(rotation, expand=True)
        
        # Pre-check with Tesseract: is this a CONSIGNMENT page at this rotation?
        try:
            text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
            is_consignment = 'CONSIGNMENT' in text.upper() and 'NOTE' in text.upper()
        except:
            is_consignment = False
        
        if not is_consignment:
            logger.info(f"[RapidOCR] No CONSIGNMENT found at rotation {rotation}°, skipping...")
            continue
        
        logger.info(f"[RapidOCR] ✓ CONSIGNMENT found at rotation {rotation}°")
        
        # Find G.C.No label position
        gc_pos, top_region = _find_gc_label_position(rotated)
        
        if gc_pos:
            logger.info(f"[RapidOCR] Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']}) with rotation {rotation}°")
            
            # Crop the number area (with bounds checking)
            crop_x1 = max(0, gc_pos['x'] + gc_pos['w'] - 30)
            crop_y1 = max(0, gc_pos['y'] - 60)
            crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 700)
            crop_y2 = min(top_region.height, gc_pos['y'] + gc_pos['h'] + 80)
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Save crop for debugging - in uploads folder
            safe_name = re.sub(r'[^\w\-.]', '_', pdf_name)
            crop_path = os.path.join(CROP_DIR, f"gc_crop_{safe_name}_p{page_num}_r{rotation}.png")
            crop.save(crop_path)
            logger.info(f"[RapidOCR] Saved crop: {crop_path}")
            
            # Use RapidOCR
            gc_num = _extract_gc_with_rapidocr(crop, pdf_name, page_num, rotation)
            if gc_num:
                logger.info(f"[RapidOCR] ✓ GC Number found at rotation {rotation}°: {gc_num}")
                return gc_num
        else:
            # Fallback: use fixed position if label not found
            logger.info(f"[RapidOCR] Label not found at {rotation}°, trying fixed position")
            try:
                crop = rotated.crop((2400, 450, 3509, 850))
                safe_name = re.sub(r'[^\w\-.]', '_', pdf_name)
                crop_path = os.path.join(CROP_DIR, f"gc_crop_{safe_name}_p{page_num}_r{rotation}_fixed.png")
                crop.save(crop_path)
                
                gc_num = _extract_gc_with_rapidocr(crop, pdf_name, page_num, rotation)
                if gc_num:
                    logger.info(f"[RapidOCR] ✓ GC Number found at fixed position, rotation {rotation}°: {gc_num}")
                    return gc_num
            except Exception as e:
                logger.warning(f"[RapidOCR] Fixed position crop failed: {e}")
    
    return None


def test_on_pdfs():
    """Test RapidOCR GC extraction on all PDFs in uploads folder"""
    
    if not HAS_RAPIDOCR:
        print("\n❌ RapidOCR is not installed. Install with: pip install rapidocr-onnxruntime")
        return
    
    # Get all PDFs in uploads folder
    pdf_files = [f for f in os.listdir(UPLOADS_DIR) if f.lower().endswith('.pdf')]
    
    print("\n" + "=" * 70)
    print("Testing RapidOCR (ONNX - NO AVX REQUIRED) for GC Number Extraction")
    print(f"Total PDFs found: {len(pdf_files)}")
    print(f"Uploads folder: {UPLOADS_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 70)
    
    results = []
    all_output = []
    all_output.append("=" * 70)
    all_output.append("RapidOCR GC Number Extraction Results (Linux Server)")
    all_output.append("=" * 70)
    all_output.append("")
    
    for pdf_idx, pdf_name in enumerate(sorted(pdf_files), 1):
        pdf_path = os.path.join(UPLOADS_DIR, pdf_name)
        
        print(f"\n[{pdf_idx}/{len(pdf_files)}] 📄 Processing: {pdf_name}")
        all_output.append(f"\n[{pdf_idx}] PDF: {pdf_name}")
        all_output.append("-" * 50)
        
        try:
            # Convert to images at 300 DPI
            pages = convert_from_path(pdf_path, dpi=300)
            
            for page_num, page in enumerate(pages, 1):
                # Try to detect if this is a consignment page - check ALL 4 rotations
                is_consignment = False
                try:
                    for rot in [0, 90, 180, 270]:
                        if rot == 0:
                            rotated = page
                        else:
                            rotated = page.rotate(rot, expand=True)
                        text = pytesseract.image_to_string(rotated, config='--psm 6')
                        if 'CONSIGNMENT' in text.upper():
                            is_consignment = True
                            logger.info(f"  [Detection] CONSIGNMENT found at rotation {rot}°")
                            break
                except:
                    is_consignment = False
                
                if is_consignment:
                    print(f"  Page {page_num}: CONSIGNMENT page detected")
                    all_output.append(f"  Page {page_num}: CONSIGNMENT")
                    
                    gc_number = extract_gc_with_rapidocr(page, pdf_name, page_num)
                    
                    if gc_number:
                        print(f"    ✓ GC Number: {gc_number}")
                        all_output.append(f"    ✓ GC Number: {gc_number}")
                        results.append((pdf_name, page_num, gc_number, "success"))
                    else:
                        print(f"    ✗ GC Number: NOT FOUND")
                        all_output.append(f"    ✗ GC Number: NOT FOUND")
                        results.append((pdf_name, page_num, None, "not_found"))
                else:
                    print(f"  Page {page_num}: INVOICE page (skipping GC extraction)")
                    all_output.append(f"  Page {page_num}: INVOICE (skipped)")
                    
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_output.append(f"  ✗ ERROR: {str(e)[:100]}")
            results.append((pdf_name, 0, None, f"error: {e}"))
    
    # Summary
    summary = []
    summary.append("\n" + "=" * 70)
    summary.append("SUMMARY")
    summary.append("=" * 70)
    
    success = len([r for r in results if r[3] == "success"])
    not_found = len([r for r in results if r[3] == "not_found"])
    errors = len([r for r in results if r[3].startswith("error")])
    
    summary.append(f"Total consignment pages tested: {len(results)}")
    summary.append(f"  ✓ GC found: {success}")
    summary.append(f"  ✗ GC not found: {not_found}")
    summary.append(f"  ⚠ Errors: {errors}")
    
    if results:
        summary.append("\nDetailed Results:")
        for pdf, page, gc, status in results:
            summary.append(f"  {pdf} Page {page}: {gc or 'N/A'} ({status})")
    
    for line in summary:
        print(line)
        all_output.append(line)
    
    # Save to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_output))
    
    print(f"\n✓ Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    test_on_pdfs()
