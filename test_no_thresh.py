"""
Try OCR directly on the COLOR adjusted image (no threshold)
"""
import cv2
import numpy as np
import pytesseract
import re

ADJUSTED = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_adjusted.png"
WORKING = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_2_1767220502439.png"

print("=" * 50)
print("OCR WITHOUT THRESHOLD")
print("=" * 50)

# Test on WORKING (3rd image - the purple one)
print("\n=== WORKING IMAGE ===")
working = cv2.imread(WORKING)
gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
scaled = cv2.resize(gray, None, fx=2, fy=2)

# NO threshold - just scaled
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(scaled, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  No-Thresh PSM{psm}: '{raw}' -> '{digits}'")

# WITH threshold
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("working_thresh.png", thresh)
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  Thresh PSM{psm}: '{raw}' -> '{digits}'")

# Test on ADJUSTED
print("\n=== ADJUSTED IMAGE ===")
adjusted = cv2.imread(ADJUSTED)
gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
scaled = cv2.resize(gray, None, fx=2, fy=2)

# NO threshold
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(scaled, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  No-Thresh PSM{psm}: '{raw}' -> '{digits}'")

# WITH threshold
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("adjusted_thresh.png", thresh)
for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  Thresh PSM{psm}: '{raw}' -> '{digits}'")
