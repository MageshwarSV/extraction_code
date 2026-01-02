"""
Extract and analyze Page 11 (skewed invoice) to diagnose OCR issue
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("=" * 80)
print("PAGE 11 ANALYSIS - SKEWED INVOICE DIAGNOSTIC")
print("=" * 80)

# Convert page 11
print("\n📄 Extracting page 11...")
pages = convert_from_path(pdf_path, dpi=300, first_page=11, last_page=11)
page11 = pages[0]

# Save original for analysis
page11.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page11_original.png")
print("✅ Saved original image")

# Try OCR without preprocessing
print("\n🔍 OCR WITHOUT preprocessing (what we got wrong):")
print("-" * 80)
text_raw = pytesseract.image_to_string(page11, lang='eng', config='--psm 6')
print(text_raw[:500])

# Check what was extracted for POST
from engine.extractors.branch_extractor import extract_branch_refined
branch_raw = extract_branch_refined(text_raw)
print(f"\nExtracted Branch (RAW): {branch_raw}")

print("\n" + "=" * 80)
print("NOW APPLYING SKEW CORRECTION...")
print("=" * 80)

# Convert PIL to OpenCV format
img_cv = cv2.cvtColor(np.array(page11), cv2.COLOR_RGB2BGR)
gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

# Detect and correct skew
def deskew_image(image):
    """Detect and correct image skew/rotation"""
    # Apply threshold
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Find contours
    coords = np.column_stack(np.where(thresh > 0))
    
    # Calculate angle
    angle = cv2.minAreaRect(coords)[-1]
    
    # Adjust angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Rotate image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    print(f"✅ Detected skew angle: {angle:.2f}°")
    return rotated, angle

# Deskew
img_deskewed, skew_angle = deskew_image(img_cv)

# Convert back to PIL
img_corrected = Image.fromarray(cv2.cvtColor(img_deskewed, cv2.COLOR_BGR2RGB))

# Save corrected image
img_corrected.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page11_deskewed.png")
print("✅ Saved deskewed image")

# Try OCR again with corrected image
print("\n🔍 OCR AFTER deskewing (should be better):")
print("-" * 80)
text_corrected = pytesseract.image_to_string(img_corrected, lang='eng', config='--psm 6')
print(text_corrected[:500])

# Extract again
branch_corrected = extract_branch_refined(text_corrected)
print(f"\nExtracted Branch (CORRECTED): {branch_corrected}")

print("\n" + "=" * 80)
print("COMPARISON:")
print("=" * 80)
print(f"Before Deskew: {branch_raw}")
print(f"After Deskew:  {branch_corrected}")
print(f"Skew Angle:    {skew_angle:.2f}°")
print("=" * 80)
