"""
Test extraction on the user's uploaded screenshot
"""
import cv2
import numpy as np
import pytesseract
import re

# User's uploaded image
IMG = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767218909595.png"

img = cv2.imread(IMG)
print(f"Image shape: {img.shape}")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Simple approach first
print("\n=== Raw (no processing) ===")
for psm in [6, 7, 8, 13]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(gray, config=config).strip()
    digits = re.sub(r'\D', '', text)
    print(f"  PSM {psm}: '{text}' -> '{digits}'")

# With scaling
print("\n=== Scaled 2x ===")
scaled = cv2.resize(gray, None, fx=2, fy=2)
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(scaled, config=config).strip()
    digits = re.sub(r'\D', '', text)
    print(f"  PSM {psm}: '{text}' -> '{digits}'")

# With threshold and invert
print("\n=== Threshold + Invert ===")
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', text)
    print(f"  PSM {psm}: '{text}' -> '{digits}'")
