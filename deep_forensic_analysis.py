#!/usr/bin/env python3
"""
Deep Forensic Analysis: Why is PDFKSS (machine scanned) faster than captured images?

Analyzes:
1. PDF metadata
2. Image encoding/compression 
3. Color space & bit depth
4. Resolution/DPI
5. Image preprocessing artifacts
6. Scanner-specific optimizations
"""

import fitz
from PIL import Image
import io
import sys

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*80)
print("FORENSIC ANALYSIS: PDFKSS vs CAPTURED IMAGE")
print("="*80)

def analyze_pdf(path, name):
    print(f"\n{'='*80}")
    print(f"{name.upper()}: {path}")
    print(f"{'='*80}")
    
    doc = fitz.open(path)
    page = doc[0]
    
    # 1. PDF Metadata
    print("\n[1] PDF METADATA:")
    print(f"  Creator: {doc.metadata.get('creator', 'N/A')}")
    print(f"  Producer: {doc.metadata.get('producer', 'N/A')}")
    print(f"  Format: {doc.metadata.get('format', 'N/A')}")
    
    # 2. Page Properties
    print("\n[2] PAGE PROPERTIES:")
    print(f"  Page size: {page.rect.width} x {page.rect.height}")
    print(f"  Rotation: {page.rotation}")
    print(f"  Fonts: {len(page.get_fonts())}")
    print(f"  Images: {len(page.get_images())}")
    print(f"  Text length: {len(page.get_text().strip())}")
    
    # 3. Image Analysis
    print("\n[3] IMAGE ANALYSIS:")
    images = page.get_images()
    if images:
        xref = images[0][0]
        base_image = doc.extract_image(xref)
        
        print(f"  Image XRef: {xref}")
        print(f"  Color space: {base_image['colorspace']}")
        print(f"  BPC (bits per component): {base_image['bpc']}")
        print(f"  Image size (bytes): {len(base_image['image'])}")
        print(f"  Compression: {base_image.get('ext', 'unknown')}")
        
        # Load image with PIL
        img = Image.open(io.BytesIO(base_image['image']))
        print(f"  PIL mode: {img.mode}")
        print(f"  PIL size: {img.size}")
        print(f"  PIL format: {img.format}")
        
        # Check for scanner-specific metadata
        if hasattr(img, '_getexif') and img._getexif():
            print(f"  EXIF data: Present")
        else:
            print(f"  EXIF data: None")
        
        # Analyze pixel characteristics
        import numpy as np
        arr = np.array(img)
        print(f"\n  PIXEL ANALYSIS:")
        print(f"    NumPy shape: {arr.shape}")
        print(f"    NumPy dtype: {arr.dtype}")
        print(f"    Value range: {arr.min()} - {arr.max()}")
        print(f"    Mean: {arr.mean():.1f}")
        print(f"    Std dev: {arr.std():.1f}")
        
        # Check if image is binary/thresholded
        unique_vals = len(np.unique(arr))
        print(f"    Unique values: {unique_vals}")
        if unique_vals < 100:
            print(f"    ⚠️  IMAGE IS BINARY/THRESHOLDED (scanner optimization!)")
        
        # Check for preprocessing artifacts
        if arr.dtype == np.uint8:
            hist, _ = np.histogram(arr, bins=256, range=(0, 256))
            # Check if histogram is bimodal (sign of thresholding)
            peaks = (hist > hist.mean() * 2).sum()
            if peaks < 10:
                print(f"    ⚠️  BIMODAL HISTOGRAM (scanner pre-processed!)")
    
    # 4. Stream analysis
    print("\n[4] CONTENT STREAM:")
    content = page.get_text("dict")
    print(f"  Blocks: {len(content.get('blocks', []))}")
    
    doc.close()
    return base_image if images else None

# Analyze both PDFs
pdfkss_img = analyze_pdf(pdfkss, "PDFKSS (Machine Scanned)")
captured_img = analyze_pdf(captured, "CAPTURED IMAGE (Phone Camera)")

# Comparison
print("\n" + "="*80)
print("KEY DIFFERENCES")
print("="*80)

if pdfkss_img and captured_img:
    print(f"\nColor space: PDFKSS={pdfkss_img['colorspace']} vs CAPTURED={captured_img['colorspace']}")
    print(f"BPC: PDFKSS={pdfkss_img['bpc']} vs CAPTURED={captured_img['bpc']}")
    print(f"Compression: PDFKSS={pdfkss_img.get('ext')} vs CAPTURED={captured_img.get('ext')}")
    print(f"Size ratio: {len(captured_img['image']) / len(pdfkss_img['image']):.2f}x")

print("\n" + "="*80)
print("HYPOTHESIS: Why is PDFKSS faster?")
print("="*80)
print("""
Likely reasons:
1. Scanner pre-processing: Binary/thresholded image (black/white only)
2. Optimized compression: Specialized for text documents
3. Clean capture: No camera artifacts, blur, or lighting issues
4. Consistent quality: Professional scanner vs phone camera
5. Metadata: Scanner may embed OCR hints or optimization flags
""")
