# Visual Analysis - Save pink regions for inspection
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("VISUAL ANALYSIS - Saving pink regions for inspection")
print("=" * 60)

# Get page 3 (known CONSIGNMENT page)
pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

# Save original page
page.save(f"{save_dir}\\page3_original.png")
print(f"1. Saved page3_original.png ({page.size})")

# Convert to OpenCV
img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

# Detect pink regions with wider range
lower_pink1 = np.array([140, 20, 100])
upper_pink1 = np.array([180, 255, 255])
lower_pink2 = np.array([0, 20, 100])
upper_pink2 = np.array([20, 255, 255])

mask1 = cv2.inRange(hsv, lower_pink1, upper_pink1)
mask2 = cv2.inRange(hsv, lower_pink2, upper_pink2)
mask = cv2.bitwise_or(mask1, mask2)

# Save mask
cv2.imwrite(f"{save_dir}\\page3_pink_mask.png", mask)
print("2. Saved page3_pink_mask.png (pink detection mask)")

# Find contours
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

print(f"\n3. Found {len(contours)} pink regions")

# Save each region
region_count = 0
for i, contour in enumerate(contours):
    area = cv2.contourArea(contour)
    if area > 1000:  # Minimum area
        x, y, w, h = cv2.boundingRect(contour)
        
        # Crop with padding
        pad = 20
        x1, y1 = max(0, x-pad), max(0, y-pad)
        x2, y2 = min(page.width, x+w+pad), min(page.height, y+h+pad)
        
        region = page.crop((x1, y1, x2, y2))
        
        region_count += 1
        filename = f"{save_dir}\\page3_region{region_count}.png"
        region.save(filename)
        print(f"   Region {region_count}: area={area}, size={w}x{h}, saved")

print(f"\nTotal regions saved: {region_count}")
print("=" * 60)
print("Now check the saved images in artifacts folder!")
