"""
DEEP Analysis: What's special about the WORKING purple image?
"""
import cv2
import numpy as np
import pytesseract
import re

# Working purple image
WORKING = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767220268375.png"
# Non-working crop
CROP = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_cropped.png"

print("=" * 60)
print("ANALYSIS: WORKING vs NON-WORKING")
print("=" * 60)

working = cv2.imread(WORKING)
crop = cv2.imread(CROP)

print(f"\nWORKING image: {working.shape}")
print(f"CROP image: {crop.shape}")

# Grayscale analysis
work_gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

print(f"\n=== GRAYSCALE STATS ===")
print(f"WORKING - Mean: {np.mean(work_gray):.1f}, Std: {np.std(work_gray):.1f}, Min: {np.min(work_gray)}, Max: {np.max(work_gray)}")
print(f"CROP    - Mean: {np.mean(crop_gray):.1f}, Std: {np.std(crop_gray):.1f}, Min: {np.min(crop_gray)}, Max: {np.max(crop_gray)}")

# HSV analysis
work_hsv = cv2.cvtColor(working, cv2.COLOR_BGR2HSV)
crop_hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

print(f"\n=== HSV STATS ===")
print(f"WORKING - H: {np.mean(work_hsv[:,:,0]):.1f}, S: {np.mean(work_hsv[:,:,1]):.1f}, V: {np.mean(work_hsv[:,:,2]):.1f}")
print(f"CROP    - H: {np.mean(crop_hsv[:,:,0]):.1f}, S: {np.mean(crop_hsv[:,:,1]):.1f}, V: {np.mean(crop_hsv[:,:,2]):.1f}")

# BGR analysis
print(f"\n=== BGR STATS ===")
print(f"WORKING - B: {np.mean(working[:,:,0]):.1f}, G: {np.mean(working[:,:,1]):.1f}, R: {np.mean(working[:,:,2]):.1f}")
print(f"CROP    - B: {np.mean(crop[:,:,0]):.1f}, G: {np.mean(crop[:,:,1]):.1f}, R: {np.mean(crop[:,:,2]):.1f}")

# Contrast (difference between text pixels and background)
print(f"\n=== CONTRAST (Std Dev) ===")
print(f"WORKING contrast: {np.std(work_gray):.1f}")
print(f"CROP contrast: {np.std(crop_gray):.1f}")

# Now test OCR on WORKING to confirm it works
print(f"\n=== OCR TEST ON WORKING ===")
scaled = cv2.resize(work_gray, None, fx=2, fy=2)
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("working_thresh.png", thresh)

for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")

print(f"\n=== OCR TEST ON CROP ===")
scaled = cv2.resize(crop_gray, None, fx=2, fy=2)
_, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("crop_thresh.png", thresh)

for psm in [6, 7]:
    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
    raw = pytesseract.image_to_string(thresh, config=config).strip()
    digits = re.sub(r'\D', '', raw)
    print(f"  PSM{psm}: '{raw}' -> '{digits}'")
