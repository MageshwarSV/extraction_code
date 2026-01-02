"""
Check if crop needs rotation - compare with working image
"""
import cv2
import numpy as np
import pytesseract
import re
import os

INPUT_CROP = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_cropped.png"
WORKING = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767219542625.png"

# Load both
crop = cv2.imread(INPUT_CROP)
working = cv2.imread(WORKING)

print(f"Crop: {crop.shape}")
print(f"Working: {working.shape}")

# They're similar aspect ratios (width > height)
# Crop is (235, 703) -> W:H = 3.0
# Working is (195, 663) -> W:H = 3.4

# Try rotating crop 90 degrees
print("\n=== Testing Rotated Crop ===")
rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
print(f"Rotated: {rotated.shape}")

# Convert to gray and threshold
gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
scaled = cv2.resize(gray, None, fx=2, fy=2)
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("gc_rotated.png", thresh)

for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"Rotated-PSM{psm}: '{raw}' -> '{digits}'")

# Also try the crop AS-IS (no rotation) with CLAHE
print("\n=== CLAHE on Original ===")
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)
scaled = cv2.resize(enhanced, None, fx=2, fy=2)
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("gc_clahe_v2.png", thresh)

for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"CLAHE-PSM{psm}: '{raw}' -> '{digits}'")
