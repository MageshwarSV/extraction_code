#!/usr/bin/env python3
"""Simple scanner vs camera comparison - no unicode issues"""

import fitz
from PIL import Image
import io
import numpy as np
import cv2

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*80)
print("SCANNER VS CAMERA ANALYSIS")
print("="*80)

def analyze(pdf_path, name):
    print(f"\n{name}:")
    print("-" * 80)
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    images = page.get_images()
    
    xref = images[0][0]
    base_image = doc.extract_image(xref)
    img = Image.open(io.BytesIO(base_image['image']))
    arr = np.array(img)
    
    # Grayscale for analysis
    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr
    
    # Metrics
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    
    contrast = gray.std()
    brightness = gray.mean()
    
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_strength = np.sqrt(sobel_x**2 + sobel_y**2).mean()
    
    noise_img = cv2.fastNlMeansDenoising(gray, None, h=10)
    noise_level = np.abs(gray.astype(float) - noise_img.astype(float)).mean()
    
    # Uniformity
    h, w = gray.shape
    center = gray[h//4:3*h//4, w//4:3*w//4].mean()
    corners = [
        gray[0:h//4, 0:w//4].mean(),
        gray[0:h//4, 3*w//4:w].mean(),
        gray[3*h//4:h, 0:w//4].mean(),
        gray[3*h//4:h, 3*w//4:w].mean()
    ]
    uniformity = np.std(corners + [center])
    
    bytes_per_pixel = len(base_image['image']) / (img.size[0] * img.size[1])
    
    print(f"  Size: {img.size}")
    print(f"  Sharpness: {sharpness:.1f}")
    print(f"  Contrast: {contrast:.1f}")
    print(f"  Brightness: {brightness:.1f}")
    print(f"  Edge strength: {edge_strength:.2f}")
    print(f"  Noise level: {noise_level:.2f}")
    print(f"  Light uniformity: {uniformity:.1f}")
    print(f"  Bytes/pixel: {bytes_per_pixel:.3f}")
    
    doc.close()
    
    return {
        'sharpness': sharpness,
        'contrast': contrast,
        'brightness': brightness,
        'edge': edge_strength,
        'noise': noise_level,
        'uniformity': uniformity,
        'compression': bytes_per_pixel
    }

m1 = analyze(pdfkss, "PDFKSS (Scanner)")
m2 = analyze(captured, "CAPTURED IMAGE (Phone)")

print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"\nMetric                Scanner    Camera     Winner")
print("-" *80)
print(f"Sharpness:            {m1['sharpness']:8.1f}   {m2['sharpness']:8.1f}   {'Scanner' if m1['sharpness'] > m2['sharpness'] else 'Camera'}")
print(f"Contrast:             {m1['contrast']:8.1f}   {m2['contrast']:8.1f}   {'Scanner' if m1['contrast'] > m2['contrast'] else 'Camera'}")
print(f"Edge strength:        {m1['edge']:8.2f}   {m2['edge']:8.2f}   {'Scanner' if m1['edge'] > m2['edge'] else 'Camera'}")
print(f"Noise (lower=better): {m1['noise']:8.2f}   {m2['noise']:8.2f}   {'Scanner' if m1['noise'] < m2['noise'] else 'Camera'}")
print(f"Uniformity (low=good):{m1['uniformity']:8.1f}   {m2['uniformity']:8.1f}   {'Scanner' if m1['uniformity'] < m2['uniformity'] else 'Camera'}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

# Determine the key differences
differences = []
if m1['sharpness'] > m2['sharpness'] * 1.5:
    differences.append(f"Scanner is {m1['sharpness']/m2['sharpness']:.1f}x SHARPER")
if m1['contrast'] > m2['contrast'] * 1.2:
    differences.append(f"Scanner has {m1['contrast']/m2['contrast']:.1f}x HIGHER CONTRAST")
if m2['noise'] > m1['noise'] * 1.5:
    differences.append(f"Camera has {m2['noise']/m1['noise']:.1f}x MORE NOISE")
if m2['uniformity'] > m1['uniformity'] * 1.5:
    differences.append(f"Camera has {m2['uniformity']/m1['uniformity']:.1f}x WORSE LIGHTING")

print("\nKey speed factors:")
for d in differences:
    print(f"  * {d}")

if not differences:
    print("  * Images are similar quality - speed difference must be elsewhere!")
    print("  * Try checking: DPI, preprocessing, OCR config differences")
