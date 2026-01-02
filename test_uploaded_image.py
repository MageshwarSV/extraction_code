#!/usr/bin/env python3
"""
COMPLETE FLOW TEST:
1. Apply scanner preprocessing to uploaded camera image
2. Run extraction on preprocessed image
3. Show results
"""

from PIL import Image
import numpy as np
import cv2
import time
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

# Load the uploaded camera image
uploaded_img_path = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766380941030.jpg'

print("="*80)
print("SCANNER PREPROCESSING + EXTRACTION TEST")
print("="*80)

print(f"\n[1] Loading camera-captured image...")
camera_img = Image.open(uploaded_img_path)
print(f"  Original size: {camera_img.size}")
print(f"  Mode: {camera_img.mode}")

# Save original for comparison
camera_img.save('camera_original.jpg')
print(f"  Saved: camera_original.jpg")

# [2] Apply scanner preprocessing
print(f"\n[2] Applying SCANNER-LIKE preprocessing...")
start_prep = time.time()

arr = np.array(camera_img)

# Convert to grayscale
if len(arr.shape) == 3:
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
else:
    gray = arr

print(f"  Step 1: Fix lighting uniformity...")
# Apply CLAHE for uniform brightness (like scanner)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
uniform = clahe.apply(gray)

print(f"  Step 2: Enhance contrast...")
# Using adaptive thresholding
contrast_enhanced = cv2.adaptiveThreshold(
    uniform, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    blockSize=21,
    C=10
)

print(f"  Step 3: Denoise...")
denoised = cv2.fastNlMeansDenoising(contrast_enhanced, None, h=10)

print(f"  Step 4: Sharpen...")
kernel_sharpen = np.array([
    [-1, -1, -1],
    [-1,  9, -1],
    [-1, -1, -1]
])
sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)

print(f"  Step 5: Morphological cleanup...")
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
cleaned = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, kernel)

# Convert back to PIL
scanner_like_img = Image.fromarray(cleaned)
prep_time = time.time() - start_prep

# Save preprocessed image
scanner_like_img.save('camera_scanner_preprocessed.jpg')
print(f"  Saved: camera_scanner_preprocessed.jpg")
print(f"  Preprocessing time: {prep_time:.2f}s")

# [3] Convert to PDF for extraction engine
print(f"\n[3] Converting to PDF...")
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

# Create PDF with preprocessed image
pdf_path = 'camera_preprocessed.pdf'
img_width, img_height = scanner_like_img.size

# Calculate PDF page size to match image aspect ratio
page_width = 595  # A4 width in points
page_height = int(page_width * img_height / img_width)

c = canvas.Canvas(pdf_path, pagesize=(page_width, page_height))
c.drawImage(ImageReader(scanner_like_img), 0, 0, width=page_width, height=page_height)
c.save()

print(f"  Created: {pdf_path}")

# [4] Run extraction
print(f"\n[4] Running extraction on preprocessed image...")
from engine.extractors.odsfhiaclient1_format11_format1 import run

start_extract = time.time()
result = run(pdf_path)
extract_time = time.time() - start_extract

print(f"  Extraction time: {extract_time:.2f}s")

# [5] Show results
print("\n" + "="*80)
print("EXTRACTION RESULTS")
print("="*80)

total_time = prep_time + extract_time

print(f"\nTiming Breakdown:")
print(f"  Preprocessing: {prep_time:.2f}s")
print(f"  Extraction:    {extract_time:.2f}s")
print(f"  TOTAL:         {total_time:.2f}s")

print(f"\nExtracted Data:")
for key, value in result.items():
    if key not in ['raw_ocr_text', 'final_text']:
        print(f"  {key}: {value}")

print("\n" + "="*80)
if total_time < 90:
    print(f"SUCCESS! Total time {total_time:.2f}s < 90s target!")
else:
    print(f"Still slow: {total_time:.2f}s > 90s target")
print("="*80)

print(f"\nGenerated files:")
print(f"  - camera_original.jpg (original camera image)")
print(f"  - camera_scanner_preprocessed.jpg (after scanner preprocessing)")
print(f"  - camera_preprocessed.pdf (PDF for extraction)")
print(f"\nCompare the images to see the preprocessing effect!")
