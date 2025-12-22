#!/usr/bin/env python3
"""
Test: Convert captured image to binary (like scanner) before OCR
This should dramatically speed up Tesseract processing
"""

from PIL import Image, ImageOps
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import time

poppler_bin = r"C:\poppler-25.07.0\Library\bin"
captured_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*80)
print("BINARY CONVERSION TEST")
print("="*80)

# Convert PDF to image
img = convert_from_path(captured_pdf, dpi=200, poppler_path=poppler_bin)[0]
print(f"\nOriginal image: {img.size}, mode={img.mode}")

# Test 1: OCR on original color image
print("\n[TEST 1] OCR on ORIGINAL COLOR image...")
start = time.time()
text1 = pytesseract.image_to_string(img, config='--psm 6')
time1 = time.time() - start
print(f"  Time: {time1:.1f}s")
print(f"  Chars: {len(text1)}")

# Test 2: Convert to grayscale first
print("\n[TEST 2] OCR on GRAYSCALE image...")
gray = img.convert('L')
start = time.time()
text2 = pytesseract.image_to_string(gray, config='--psm 6')
time2 = time.time() - start
print(f"  Time: {time2:.1f}s")
print(f"  Chars: {len(text2)}")

# Test 3: Convert to BINARY (like scanner)
print("\n[TEST 3] OCR on BINARY (black/white) image...")
# Enhanced binary conversion for better OCR
gray_arr = np.array(gray)

# Apply adaptive thresholding (like scanner does)
import cv2
binary_arr = cv2.adaptiveThreshold(
    gray_arr, 
    255, 
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    cv2.THRESH_BINARY, 
    blockSize=31,  # Large block size for document scanning
    C=10  # Constant subtracted from mean
)

binary_img = Image.fromarray(binary_arr)
binary_img.save('binary_test.png')
print(f"  Saved binary_test.png for inspection")

start = time.time()
text3 = pytesseract.image_to_string(binary_img, config='--psm 6')
time3 = time.time() - start
print(f"  Time: {time3:.1f}s")
print(f"  Chars: {len(text3)}")

# Test 4: Binary with noise removal
print("\n[TEST 4] OCR on BINARY + DENOISED image...")
# Morphological operations to clean up
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
cleaned = cv2.morphologyEx(binary_arr, cv2.MORPH_CLOSE, kernel)
cleaned_img = Image.fromarray(cleaned)
cleaned_img.save('binary_cleaned_test.png')

start = time.time()
text4 = pytesseract.image_to_string(cleaned_img, config='--psm 6')
time4 = time.time() - start
print(f"  Time: {time4:.1f}s")
print(f"  Chars: {len(text4)}")

# Summary
print("\n" + "="*80)
print("RESULTS SUMMARY")
print("="*80)
print(f"Original (color):       {time1:.1f}s  (baseline)")
print(f"Grayscale:             {time2:.1f}s  ({time2/time1:.2f}x)")
print(f"Binary (scanner-like): {time3:.1f}s  ({time3/time1:.2f}x) 🎯")
print(f"Binary + denoised:     {time4:.1f}s  ({time4/time1:.2f}x)")

if time3 < time1 * 0.5:
    print("\n✅ BINARY CONVERSION IS MUCH FASTER!")
    print("SOLUTION: Convert captured images to binary before OCR")
else:
    print("\n⚠️  Binary conversion didn't help significantly")
    print("Need to investigate other factors")
