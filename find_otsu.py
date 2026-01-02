"""
Find OTSU threshold value from WORKING and apply to ADJUSTED
"""
import cv2
import numpy as np
import pytesseract
import re

WORKING = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_2_1767220502439.png"
ADJUSTED = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_adjusted.png"

print("=" * 50)
print("FIND OTSU THRESHOLD VALUES")
print("=" * 50)

# WORKING
working = cv2.imread(WORKING)
work_gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
work_scaled = cv2.resize(work_gray, None, fx=2, fy=2)
otsu_val_work, work_thresh = cv2.threshold(work_scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
print(f"WORKING OTSU threshold: {otsu_val_work}")

# ADJUSTED
adjusted = cv2.imread(ADJUSTED)
adj_gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
adj_scaled = cv2.resize(adj_gray, None, fx=2, fy=2)
otsu_val_adj, adj_thresh = cv2.threshold(adj_scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
print(f"ADJUSTED OTSU threshold: {otsu_val_adj}")

# Now apply WORKING's threshold to ADJUSTED
print(f"\n=== Apply WORKING's threshold ({otsu_val_work}) to ADJUSTED ===")
_, adj_with_work_thresh = cv2.threshold(adj_scaled, otsu_val_work, 255, cv2.THRESH_BINARY)
cv2.imwrite("gc_fixed_thresh.png", adj_with_work_thresh)
print("Saved: gc_fixed_thresh.png")

for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(adj_with_work_thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")
