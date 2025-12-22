#!/usr/bin/env python3
"""
OPTIMIZED Scanner Preprocessing v2
- Gentler processing to preserve detail while still improving OCR speed
"""

from PIL import Image
import numpy as np
import cv2
import time

uploaded_img_path = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766380941030.jpg'

print("="*80)
print("OPTIMIZED SCANNER PREPROCESSING V2")
print("="*80)

camera_img = Image.open(uploaded_img_path)
arr = np.array(camera_img)

# Convert to grayscale
if len(arr.shape) == 3:
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
else:
    gray = arr

print("\n[VERSION 1] Aggressive (current)")
start = time.time()

# V1: Aggressive
clahe1 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
uniform1 = clahe1.apply(gray)
thresh1 = cv2.adaptiveThreshold(uniform1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=21, C=10)
denoised1 = cv2.fastNlMeansDenoising(thresh1, None, h=10)
kernel_sharpen = np.array([[-1, -1, -1], [-1,  9, -1], [-1, -1, -1]])
sharpened1 = cv2.filter2D(denoised1, -1, kernel_sharpen)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
result_v1 = cv2.morphologyEx(sharpened1, cv2.MORPH_CLOSE, kernel)

time_v1 = time.time() - start
Image.fromarray(result_v1).save('preprocessed_v1_aggressive.jpg')
print(f"  Time: {time_v1:.2f}s")
print(f"  Saved: preprocessed_v1_aggressive.jpg")

print("\n[VERSION 2] Balanced (RECOMMENDED)")
start = time.time()

# V2: Balanced - less aggressive, preserve detail
clahe2 = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))  # Higher clip limit = less aggressive
uniform2 = clahe2.apply(gray)
# Smaller block size + higher C = preserve more detail
thresh2 = cv2.adaptiveThreshold(uniform2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=15, C=8)
# Less denoising
denoised2 = cv2.fastNlMeansDenoising(thresh2, None, h=5)
# Skip sharpening - camera images are already sharp
# Skip morphology - preserve character spacing
result_v2 = denoised2

time_v2 = time.time() - start
Image.fromarray(result_v2).save('preprocessed_v2_balanced.jpg')
print(f"  Time: {time_v2:.2f}s")
print(f"  Saved: preprocessed_v2_balanced.jpg")

print("\n[VERSION 3] Minimal (fastest)")
start = time.time()

# V3: Minimal - just fix lighting, keep rest as-is
clahe3 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
result_v3 = clahe3.apply(gray)

time_v3 = time.time() - start
Image.fromarray(result_v3).save('preprocessed_v3_minimal.jpg')
print(f"  Time: {time_v3:.2f}s")
print(f"  Saved: preprocessed_v3_minimal.jpg")

print("\n" + "="*80)
print("COMPARISON")
print("="*80)
print(f"\nV1 Aggressive: {time_v1:.2f}s - High contrast, may lose detail")
print(f"V2 Balanced:   {time_v2:.2f}s - Good balance (RECOMMENDED)")
print(f"V3 Minimal:    {time_v3:.2f}s - Fastest, preserves most detail")

print("\nGenerated 3 versions for comparison!")
print("Check which one gives best OCR results vs speed tradeoff.")
