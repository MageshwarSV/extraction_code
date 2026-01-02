"""
Test OCR on the WORKING purple image (user uploaded)
"""
import cv2
import numpy as np
import pytesseract
import re

# User's purple image that works
IMG = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767219542625.png"

img = cv2.imread(IMG)
print(f"Shape: {img.shape}")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Test various configs
print("\n=== Raw Gray ===")
for psm in [6, 7, 8]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(gray, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")

# Scale 2x
scaled = cv2.resize(gray, None, fx=2, fy=2)
print("\n=== Scaled 2x ===")
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(scaled, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")

# Simple threshold
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
print("\n=== Threshold ===")
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")
