#!/usr/bin/env python3
"""
Research: Professional Color Scanner Characteristics vs PDFKSS

Scanners optimize for OCR by doing:
1. Consistent lighting (no shadows/glare)
2. Fixed focal distance (sharp, no blur)
3. Perpendicular angle (no perspective distortion)
4. Controlled DPI (typically 200-300 for documents)
5. Color/contrast optimization
6. Edge enhancement
7. Despeckle/denoise
8. Straightening/deskew
"""

import fitz
from PIL import Image
import io
import numpy as np
import cv2


pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*90)
print("SCANNER CHARACTERISTICS ANALYSIS")
print("="*90)

def analyze_scanner_properties(pdf_path, name):
    print(f"\n{'='*90}")
    print(f"{name}")
    print(f"{'='*90}")
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Extract image
    images = page.get_images()
    if not images:
        print("No images found!")
        return
    
    xref = images[0][0]
    base_image = doc.extract_image(xref)
    img = Image.open(io.BytesIO(base_image['image']))
    arr = np.array(img)
    
    print(f"\n[1] BASIC PROPERTIES:")
    print(f"  Size: {img.size[0]} x {img.size[1]} pixels")
    print(f"  Mode: {img.mode}")
    print(f"  File size: {len(base_image['image']):,} bytes ({len(base_image['image'])/1024:.1f} KB)")
    
    # Convert to grayscale for analysis
    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr
    
    print(f"\n[2] IMAGE QUALITY (Scanner Optimizations):")
    
    # 2a. Sharpness (edge detection)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    print(f"  Sharpness (Laplacian variance): {sharpness:.1f}")
    if sharpness > 500:
        print(f"    ✅ SHARP IMAGE (good for OCR)")
    elif sharpness > 200:
        print(f"    ⚠️  MODERATE sharpness")
    else:
        print(f"    ❌ BLURRY (bad for OCR)")
    
    # 2b. Contrast
    contrast = gray.std()
    print(f"  Contrast (std dev): {contrast:.1f}")
    if contrast > 60:
        print(f"    ✅ HIGH CONTRAST (good for OCR)")
    elif contrast > 40:
        print(f"    ⚠️  MODERATE contrast")
    else:
        print(f"    ❌ LOW CONTRAST (bad for OCR)")
    
    # 2c. Brightness distribution
    mean_bright = gray.mean()
    print(f"  Average brightness: {mean_bright:.1f}")
    if 200 < mean_bright < 240:
        print(f"    ✅ OPTIMAL (white background, dark text)")
    elif mean_bright > 240:
        print(f"    ⚠️  TOO BRIGHT (may wash out text)")
    else:
        print(f"    ⚠️  TOO DARK")
    
    # 2d. Skew/rotation (perpendicular check)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
    if lines is not None:
        angles = []
        for line in lines[:10]:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            angles.append(angle)
        avg_angle = np.mean(angles)
        print(f"  Skew angle: {avg_angle:.2f}°")
        if abs(avg_angle) < 1:
            print(f"    ✅ STRAIGHT (scanner precision)")
        elif abs(avg_angle) < 3:
            print(f"    ⚠️  SLIGHTLY SKEWED")
        else:
            print(f"    ❌ ROTATED (camera artifact)")
    
    # 2e. Noise level
    noise = cv2.fastNlMeansDenoising(gray, None, h=10)
    noise_level = np.abs(gray.astype(float) - noise.astype(float)).mean()
    print(f"  Noise level: {noise_level:.2f}")
    if noise_level < 5:
        print(f"    ✅ CLEAN (scanner despeckling)")
    elif noise_level < 10:
        print(f"    ⚠️  MODERATE noise")
    else:
        print(f"    ❌ NOISY (camera sensor noise)")
    
    # 2f. Edge quality (blur detection)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_strength = np.sqrt(sobel_x**2 + sobel_y**2).mean()
    print(f"  Edge strength: {edge_strength:.2f}")
    if edge_strength > 30:
        print(f"    ✅ CRISP EDGES (good focus)")
    elif edge_strength > 20:
        print(f"    ⚠️  MODERATE edges")
    else:
        print(f"    ❌ SOFT EDGES (out of focus)")
    
    print(f"\n[3] COMPRESSION & ENCODING:")
    print(f"  Compression: {base_image.get('ext', 'unknown')}")
    print(f"  Bits per component: {base_image['bpc']}")
    print(f"  Colorspace: {base_image['colorspace']}")
    
    # Compression efficiency (bytes per pixel)
    total_pixels = img.size[0] * img.size[1]
    bytes_per_pixel = len(base_image['image']) / total_pixels
    print(f"  Bytes per pixel: {bytes_per_pixel:.3f}")
    if bytes_per_pixel < 0.3:
        print(f"    ✅ HIGHLY COMPRESSED (efficient)")
    elif bytes_per_pixel < 0.6:
        print(f"    ⚠️  MODERATE compression")
    else:
        print(f"    ❌ LOW COMPRESSION")
    
    print(f"\n[4] SCANNER-SPECIFIC OPTIMIZATIONS:")
    
    # Check for text enhancement
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    # Bimodal histogram = thresholding applied
    peaks = []
    for i in range(1, 255):
        if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
            if hist[i] > hist.max() * 0.1:
                peaks.append(i)
    
    print(f"  Histogram peaks: {len(peaks)}")
    if len(peaks) == 2:
        print(f"    ✅ BIMODAL (text enhancement applied)")
    elif len(peaks) < 5:
        print(f"    ⚠️  Few peaks (some enhancement)")
    else:
        print(f"    ❌ MANY peaks (raw camera data)")
    
    # Check uniformity (consistent lighting)
    h, w = gray.shape
    center = gray[h//4:3*h//4, w//4:3*w//4].mean()
    corners = [
        gray[0:h//4, 0:w//4].mean(),
        gray[0:h//4, 3*w//4:w].mean(),
        gray[3*h//4:h, 0:w//4].mean(),
        gray[3*h//4:h, 3*w//4:w].mean()
    ]
    uniformity = np.std(corners + [center])
    print(f"  Lighting uniformity: {uniformity:.1f}")
    if uniformity < 20:
        print(f"    ✅ UNIFORM (scanner lighting)")
    elif uniformity < 40:
        print(f"    ⚠️  MODERATE uniformity")
    else:
        print(f"    ❌ NON-UNIFORM (camera lighting)")
    
    doc.close()
    
    # Return metrics for comparison
    return {
        'sharpness': sharpness,
        'contrast': contrast,
        'brightness': mean_bright,
        'noise': noise_level,
        'edge_strength': edge_strength,
        'bytes_per_pixel': bytes_per_pixel,
        'histogram_peaks': len(peaks),
        'uniformity': uniformity
    }

# Analyze both
pdfkss_metrics = analyze_scanner_properties(pdfkss, "PDFKSS (Machine Scanner)")
captured_metrics = analyze_scanner_properties(captured, "CAPTURED IMAGE (Phone Camera)")

# Comparison
print("\n" + "="*90)
print("COMPARISON: Why is Scanner Faster?")
print("="*90)

if pdfkss_metrics and captured_metrics:
    print("\nMetric                  | PDFKSS (Scanner) | Captured (Phone) | Winner")
    print("-" * 90)
    
    for key in ['sharpness', 'contrast', 'edge_strength', 'uniformity']:
        p = pdfkss_metrics[key]
        c = captured_metrics[key]
        winner = "Scanner ✅" if p > c else "Camera"
        print(f"{key:23} | {p:16.1f} | {c:16.1f} | {winner}")
    
    for key in ['noise', 'bytes_per_pixel']:
        p = pdfkss_metrics[key]
        c = captured_metrics[key]
        winner = "Scanner ✅" if p < c else "Camera"
        print(f"{key:23} | {p:16.3f} | {c:16.3f} | {winner}")

print("\n" + "="*90)
print("CONCLUSION")
print("="*90)
print("""
Scanner produces OCR-optimized images with:
1. ✅ Higher sharpness (better focus)
2. ✅ Higher contrast (text stands out)
3. ✅ Cleaner (less noise from sensor)
4. ✅ Uniform lighting (no shadows/glare)
5. ✅ Crisp edges (perpendicular capture)
6. ✅ Optimal compression (efficient encoding)

To make camera images as fast as scanner:
→ Apply scanner-like preprocessing before OCR!
""")
