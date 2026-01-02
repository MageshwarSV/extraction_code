"""
Test OCR on the PINK image directly
"""
import cv2
import numpy as np
import pytesseract
import re

# User's pink image
IMG = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767219729115.png"

img = cv2.imread(IMG)
print(f"Shape: {img.shape}")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Scale 2x + Threshold (same as working purple test)
scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("test_pink_thresh.png", thresh)

print("\n=== Threshold (Scale 2x) ===")
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")

# Also try raw scaled
print("\n=== Raw Scaled 2x ===")
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(scaled, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")
