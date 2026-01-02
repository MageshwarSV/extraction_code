"""
Quick test to analyze Format 2 invoice with Tesseract OCR
This will help identify what's different from Format 1
"""

import sys
import os
from PIL import Image
import pytesseract

# Point to uploaded Format 2 invoice
format2_image_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/uploaded_image_1766467732793.jpg"

# Load image
img = Image.open(format2_image_path)

# Run basic OCR
text = pytesseract.image_to_string(img, lang='eng')

print("=" * 80)
print("FORMAT 2 INVOICE - OCR TEXT ANALYSIS")
print("=" * 80)
print(text)
print("\n" + "=" * 80)
print("KEY OBSERVATIONS:")
print("=" * 80)

# Check for key fields
observations = []

if "Invoice No" in text or "Invoice" in text:
    observations.append("✓ Invoice number field present")
if "L.R" in text or "LR" in text or "RR" in text:
    observations.append("✓ L.R./RR number field present")
if "E-Way" in text or "EWB" in text:
    observations.append("✓ E-Way Bill field present")
if "Consignee" in text or "Recipient" in text:
    observations.append("✓ Consignee field present")
if "Vehicle" in text:
    observations.append("✓ Vehicle field present")
if "Destination" in text or "Place of Supply" in text:
    observations.append("✓ Destination field present")

for obs in observations:
    print(obs)

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Compare this output with Format 1 extraction patterns")
print("2. Identify regex patterns that need updating")
print("3. Test extraction functions from client1_format1.py")
