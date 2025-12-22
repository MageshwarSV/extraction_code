#!/usr/bin/env python3
"""
CRITICAL TEST: Does preprocessing actually help or hurt?

Compare:
1. NO preprocessing (just grayscale)
2. V3 Minimal (CLAHE only)
3. Original camera image
"""

from PIL import Image
import pytesseract
import time

uploaded = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766380941030.jpg'

img = Image.open(uploaded)

print("="*80)
print("OCR SPEED TEST - Does preprocessing help?")
print("="*80)

# Test 1: Original color
print("\n[1] Original COLOR image...")
start = time.time()
text1 = pytesseract.image_to_string(img, config='--psm 6')
time1 = time.time() - start
print(f"  Time: {time1:.2f}s")
print(f"  Chars: {len(text1)}")

# Test 2: Simple grayscale (no preprocessing)
print("\n[2] Simple GRAYSCALE (no preprocessing)...")
gray = img.convert('L')
start = time.time()
text2 = pytesseract.image_to_string(gray, config='--psm 6')
time2 = time.time() - start
print(f"  Time: {time2:.2f}s")
print(f"  Chars: {len(text2)}")

# Test 3: V3 Minimal (CLAHE)
print("\n[3] V3 Minimal (CLAHE lighting fix)...")
import cv2
import numpy as np
arr = np.array(gray)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
clahe_img = Image.fromarray(clahe.apply(arr))
start = time.time()
text3 = pytesseract.image_to_string(clahe_img, config='--psm 6')
time3 = time.time() - start
print(f"  Time: {time3:.2f}s")
print(f"  Chars: {len(text3)}")

print("\n" + "="*80)
print("RESULTS")
print("="*80)
print(f"\n1. Original:   {time1:.2f}s ({len(text1)} chars)")
print(f"2. Grayscale:  {time2:.2f}s ({len(text2)} chars) - {time1/time2:.2f}x")
print(f"3. CLAHE:      {time3:.2f}s ({len(text3)} chars) - {time1/time3:.2f}x")

if time2 < time3:
    print("\n*** GRAYSCALE is actually FASTER than CLAHE! ***")
    print("Preprocessing is SLOWING US DOWN!")
else:
    print(f"\nCLAHE gives {time2/time3:.2f}x speedup over grayscale")
