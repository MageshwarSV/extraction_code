#!/usr/bin/env python3
"""
FINAL ANALYSIS: Why is PDFKSS actually 2-5x faster at OCR?

Both need OCR, both are images, but PDFKSS is much faster.
What's different?
"""

import fitz
from PIL import Image
import io
import pytesseract
import time

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*80)
print("CRITICAL COMPARISON: PDFKSS vs CAPTURED")
print("="*80)

def analyze_and_ocr(pdf_path, name):
    print(f"\n[{name}]")
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Extract image
    images = page.get_images()
    xref = images[0][0]
    base_image = doc.extract_image(xref)
    img = Image.open(io.BytesIO(base_image['image']))
    
    print(f"  Image size: {img.size[0]} x {img.size[1]} pixels")
    print(f"  Total pixels: {img.size[0] * img.size[1]:,}")
    print(f"  File size: {len(base_image['image']):,} bytes")
    print(f"  Mode: {img.mode}")
    print(f"  Compression: {base_image.get('ext', 'unknown')}")
    
    # Calculate megapixels
    mp = (img.size[0] * img.size[1]) / 1_000_000
    print(f"  Megapixels: {mp:.2f} MP")
    
    # Convert to grayscale for OCR test
    gray = img.convert('L')
    
    # Test OCR speed on a CROP (to save time)
    # Take middle 20% of image
    w, h = gray.size
    crop = gray.crop((int(w*0.4), int(h*0.4), int(w*0.6), int(h*0.6)))
    
    print(f"\n  OCR Test (on 20% crop):")
    start = time.time()
    text = pytesseract.image_to_string(crop, config='--psm 6')
    ocr_time = time.time() - start
    print(f"    Time: {ocr_time:.2f}s")
    print(f"    Chars extracted: {len(text)}")
    
    # Estimate full image OCR time
    estimated_full = ocr_time * 25  # 20% crop = 1/25 of area
    print(f"    Estimated full image: {estimated_full:.2f}s")
    
    doc.close()
    
    return {
        'pixels': img.size[0] * img.size[1],
        'mp': mp,
        'ocr_time_crop': ocr_time,
        'estimated_full': estimated_full
    }

pdfkss_data = analyze_and_ocr(pdfkss, "PDFKSS (Scanner)")
captured_data = analyze_and_ocr(captured, "CAPTURED IMAGE (Camera)")

print("\n" + "="*80)
print("COMPARISON")
print("="*80)

ratio_pixels = captured_data['pixels'] / pdfkss_data['pixels']
ratio_ocr = captured_data['estimated_full'] / pdfkss_data['estimated_full']

print(f"\nPixel count ratio: {ratio_pixels:.2f}x")
print(f"OCR time ratio: {ratio_ocr:.2f}x")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if ratio_pixels > 2:
    print(f"\n*** FOUND IT! Camera image has {ratio_pixels:.1f}x MORE PIXELS ***")
    print("\nCamera images are higher resolution than scanner!")
    print(f"  PDFKSS: {pdfkss_data['pixels']:,} pixels ({pdfkss_data['mp']:.1f} MP)")
    print(f"  Camera: {captured_data['pixels']:,} pixels ({captured_data['mp']:.1f} MP)")
    print("\nSOLUTION:")
    print("  → RESIZE camera images to match scanner resolution")
    print(f"  → Target: ~{pdfkss_data['mp']:.1f} MP instead of {captured_data['mp']:.1f} MP")
    print(f"  → This will make OCR {ratio_ocr:.1f}x FASTER!")
elif ratio_ocr > 2:
    print("\nOCR is slower but pixel count is similar")
    print("The difference must be in image characteristics")
else:
    print("\nSimilar speed - investigate other factors")
