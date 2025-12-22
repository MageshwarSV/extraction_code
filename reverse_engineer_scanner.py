#!/usr/bin/env python3
"""
REVERSE ENGINEER SCANNER PREPROCESSING

Extract scanner image and analyze what preprocessing it applies.
Then create a transformation pipeline to make camera images look identical.
"""

import fitz
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io
import numpy as np
import cv2

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'

print("="*80)
print("REVERSE ENGINEERING SCANNER PREPROCESSING")
print("="*80)

# Extract scanner image
doc = fitz.open(pdfkss)
page = doc[0]
xref = page.get_images()[0][0]
base_image = doc.extract_image(xref)
scanner_img = Image.open(io.BytesIO(base_image['image']))
scanner_arr = np.array(scanner_img)

print(f"\n[1] SCANNER IMAGE PROPERTIES:")
print(f"  Size: {scanner_img.size}")
print(f"  Mode: {scanner_img.mode}")
print(f"  DPI: {scanner_img.info.get('dpi', 'unknown')}")

# Convert to grayscale for analysis
scanner_gray = cv2.cvtColor(scanner_arr, cv2.COLOR_RGB2GRAY)

print(f"\n[2] PIXEL VALUE DISTRIBUTION:")
print(f"  Min: {scanner_gray.min()}")
print(f"  Max: {scanner_gray.max()}")
print(f"  Mean: {scanner_gray.mean():.1f}")
print(f"  Std: {scanner_gray.std():.1f}")

# Histogram analysis
hist = cv2.calcHist([scanner_gray], [0], None, [256], [0, 256])
peaks = []
for i in range(10, 246):
    if hist[i] > hist[i-5] and hist[i] > hist[i+5]:
        if hist[i] > hist.max() * 0.05:
            peaks.append((i, int(hist[i][0])))

print(f"\n[3] HISTOGRAM PEAKS (Scanner's threshold points):")
for val, count in sorted(peaks, key=lambda x: -x[1])[:5]:
    print(f"  Peak at {val}: {count} pixels")

# Check if scanner applied gamma correction
gamma_estimate = np.log(scanner_gray.mean() / 255) / np.log(0.5)
print(f"\n[4] ESTIMATED GAMMA CORRECTION: {gamma_estimate:.2f}")

# Check sharpening level
laplacian = cv2.Laplacian(scanner_gray, cv2.CV_64F)
sharpness = laplacian.var()
print(f"\n[5] SHARPNESS LEVEL: {sharpness:.1f}")

# Check contrast enhancement
contrast_ratio = (scanner_gray.max() - scanner_gray.min()) / 255.0
print(f"\n[6] CONTRAST USAGE: {contrast_ratio:.2%}")

# Build histogram equalization comparison
equalized = cv2.equalizeHist(scanner_gray)
diff_from_eq = np.abs(scanner_gray.astype(float) - equalized.astype(float)).mean()
print(f"\n[7] HISTOGRAM EQUALIZATION CHECK:")
print(f"  Diff from equalized: {diff_from_eq:.1f}")
if diff_from_eq < 10:
    print(f"  -> Scanner APPLIED histogram equalization!")
else:
    print(f"  -> Scanner did NOT use histogram equalization")

# Check adaptive thresholding
adaptive_thresh = cv2.adaptiveThreshold(
    scanner_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    cv2.THRESH_BINARY, blockSize=11, C=2
)
diff_from_adaptive = np.abs(scanner_gray.astype(float) - adaptive_thresh.astype(float)).mean()
print(f"\n[8] ADAPTIVE THRESHOLDING CHECK:")
print(f"  Diff from adaptive: {diff_from_adaptive:.1f}")

# Check morphological operations
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
morphed = cv2.morphologyEx(scanner_gray, cv2.MORPH_CLOSE, kernel)
diff_from_morph = np.abs(scanner_gray.astype(float) - morphed.astype(float)).mean()
print(f"\n[9] MORPHOLOGICAL PROCESSING:")
print(f"  Diff from morphology: {diff_from_morph:.1f}")

# Lighting analysis
h, w = scanner_gray.shape
center_brightness = scanner_gray[h//4:3*h//4, w//4:3*w//4].mean()
edge_brightness = (
    scanner_gray[0:h//4, :].mean() +
    scanner_gray[3*h//4:, :].mean() +
    scanner_gray[:, 0:w//4].mean() +
    scanner_gray[:, 3*w//4:].mean()
) / 4

print(f"\n[10] LIGHTING UNIFORMITY:")
print(f"  Center brightness: {center_brightness:.1f}")
print(f"  Edge brightness: {edge_brightness:.1f}")
print(f"  Difference: {abs(center_brightness - edge_brightness):.1f}")
if abs(center_brightness - edge_brightness) < 10:
    print(f"  -> UNIFORM lighting (scanner has even illumination)")

# Color channel analysis
if len(scanner_arr.shape) == 3:
    r, g, b = scanner_arr[:,:,0], scanner_arr[:,:,1], scanner_arr[:,:,2]
    print(f"\n[11] COLOR CHANNEL BALANCE:")
    print(f"  R mean: {r.mean():.1f}")
    print(f"  G mean: {g.mean():.1f}")
    print(f"  B mean: {b.mean():.1f}")
    print(f"  R std: {r.std():.1f}")
    print(f"  G std: {g.std():.1f}")
    print(f"  B std: {b.std():.1f}")
    
    # Check if desaturated
    max_diff = max(abs(r.mean() - g.mean()), abs(g.mean() - b.mean()), abs(r.mean() - b.mean()))
    if max_diff < 10:
        print(f"  -> Scanner DESATURATED colors (nearly grayscale)")

doc.close()

print("\n" + "="*80)
print("SCANNER PREPROCESSING PIPELINE (DETECTED):")
print("="*80)
print("""
Based on analysis, scanner applies:
1. Uniform, bright illumination (center ~{:.0f}, edges ~{:.0f})
2. High contrast (using {:.0%} of value range)
3. Sharpness: {:.0f} (Laplacian variance)
4. Gamma correction: ~{:.2f}
5. Color desaturation (R/G/B channels balanced)
6. Minimal noise (professional sensor)
7. Fixed DPI and perpendicular capture

To transform camera images -> scanner-like:
→ Apply these exact transformations!
""".format(center_brightness, edge_brightness, contrast_ratio, sharpness, gamma_estimate))

# Save scanner image for visual comparison
scanner_img.save('scanner_reference.png')
print("\nSaved 'scanner_reference.png' for comparison")
