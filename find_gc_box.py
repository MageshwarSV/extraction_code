# Find small rectangular GC box (based on user's image)
# The G.C.No box is approximately 50-100 pixels wide, 100-300 pixels tall
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image, ImageOps
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Finding GC Box - Small rectangular pink regions")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

# Convert to OpenCV
img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

# Pink detection
lower_pink = np.array([140, 30, 100])
upper_pink = np.array([180, 255, 255])
mask = cv2.inRange(hsv, lower_pink, upper_pink)

# Clean mask
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

print(f"Found {len(contours)} total pink contours\n")
print("Filtering for small GC box candidates:")
print(f"{'#':<4} {'Size':<15} {'Area':<10} {'Aspect':<8}")
print("-" * 50)

gc_candidates = []
for i, contour in enumerate(contours):
    x, y, w, h = cv2.boundingRect(contour)
    area = cv2.contourArea(contour)
    aspect = h / w if w > 0 else 0
    
    # GC box filter: small width (40-120px), moderate height (100-400px), vertical aspect
    if 40 < w < 150 and 100 < h < 500 and aspect > 1.5:
        gc_candidates.append((x, y, w, h, area, aspect))
        print(f"{len(gc_candidates):<4} {w}x{h:<10} {int(area):<10} {aspect:.2f}")

print(f"\n{len(gc_candidates)} GC box candidates found")

# Save and OCR each candidate
for idx, (x, y, w, h, area, aspect) in enumerate(gc_candidates, 1):
    # Crop with padding
    pad = 10
    x1, y1 = max(0, x-pad), max(0, y-pad)
    x2, y2 = min(page.width, x+w+pad), min(page.height, y+h+pad)
    
    region = page.crop((x1, y1, x2, y2))
    region.save(f"{save_dir}\\gc_candidate_{idx}.png")
    
    # Try OCR at 0 and 90 degrees with digit whitelist
    print(f"\nCandidate {idx} OCR:")
    for angle in [0, 90, 180, 270]:
        rot = region if angle == 0 else region.rotate(angle, expand=True)
        
        # Enhance
        gray = ImageOps.grayscale(rot)
        gray = ImageOps.autocontrast(gray)
        
        text = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789', lang='eng')
        text = text.strip()
        if text:
            print(f"  {angle}: {text}")

print("\n" + "=" * 60)
