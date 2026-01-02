"""
Script 2: Extract GC from Crop - EXACT COPY OF WORKING LOGIC from find_otsu.py
"""
import cv2
import numpy as np
import pytesseract
import re
import os

ADJUSTED = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_adjusted.png"
THRESHOLD = 126.0

def extract():
    print("=" * 50)
    print("GC EXTRACTION")
    print("=" * 50)
    
    adjusted = cv2.imread(ADJUSTED)
    if adjusted is None:
        print(f"Error: Cannot read {ADJUSTED}")
        return None
    
    adj_gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
    adj_scaled = cv2.resize(adj_gray, None, fx=2, fy=2)
    _, adj_with_work_thresh = cv2.threshold(adj_scaled, THRESHOLD, 255, cv2.THRESH_BINARY)
    
    config = '--psm 6 -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(adj_with_work_thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    
    print(f"PSM6: '{raw}' -> '{digits}'")
    return digits

if __name__ == "__main__":
    result = extract()
    print(f"\nFINAL: {result}")
