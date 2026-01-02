"""
Minimal test: Run OCR on the saved debug_gc_WINNER_rot180.png
using the exact ProvenWinner config (2x + Erode + Invert + PSM 6)
"""
import cv2
import numpy as np
import pytesseract
import os

IMG_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_WINNER_rot180.png"

def test_ocr():
    if not os.path.exists(IMG_PATH):
        print(f"Image not found: {IMG_PATH}")
        return
    
    print(f"Testing: {os.path.basename(IMG_PATH)}")
    img = cv2.imread(IMG_PATH)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # ProvenWinner Config: 2x Scale + Erode + Invert + PSM 6
    scaled_2x = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    kernel = np.ones((2,2), np.uint8)
    eroded = cv2.erode(scaled_2x, kernel, iterations=1)
    _, thresh = cv2.threshold(eroded, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inverted = cv2.bitwise_not(thresh)
    
    # OCR
    config = '--psm 6 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(inverted, config=config).strip()
    
    print(f"\nRaw OCR Output: '{text}'")
    
    # Extract digits
    import re
    digits = re.sub(r'\D', '', text)
    print(f"Extracted Digits: '{digits}'")
    
    if digits == "14549":
        print("\n[SUCCESS] Correctly extracted 14549!")
    else:
        print(f"\n[MISMATCH] Expected 14549, got '{digits}'")

if __name__ == "__main__":
    test_ocr()
