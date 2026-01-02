import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageFilter
import logging

logging.basicConfig(level=logging.WARNING)

print("Debugging Page 3 - Saving cropped regions")
print("=" * 60)

pages = convert_from_path(
    r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf',
    dpi=300,  # Higher DPI for better quality
    first_page=3,
    last_page=3
)

page = pages[0]
img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

# Detect pink regions
lower_pink1 = np.array([140, 20, 20])
upper_pink1 = np.array([180, 255, 255])
lower_pink2 = np.array([0, 20, 80])
upper_pink2 = np.array([20, 255, 255])

mask1 = cv2.inRange(hsv, lower_pink1, upper_pink1)
mask2 = cv2.inRange(hsv, lower_pink2, upper_pink2)
mask = cv2.bitwise_or(mask1, mask2)

kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask = cv2.dilate(mask, kernel, iterations=2)

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)

print(f"Found {len(contours)} regions\n")

for idx, contour in enumerate(contours[:3]):
    area = cv2.contourArea(contour)
    if area < 500:
        continue
    
    x, y, w, h = cv2.boundingRect(contour)
    padding = 30
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(img_cv.shape[1] - x, w + 2*padding)
    h = min(img_cv.shape[0] - y, h + 2*padding)
    
    region = img_cv[y:y+h, x:x+w]
    region_pil = Image.fromarray(cv2.cvtColor(region, cv2.COLOR_BGR2RGB))
    
    print(f"Region {idx+1}: {w}x{h}px at ({x},{y})")
    
    # Save original region
    save_path = rf"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page3_region{idx+1}_original.png"
    region_pil.save(save_path)
    print(f"  Saved original: page3_region{idx+1}_original.png")
    
    # Apply deskew
    from engine.extractors.deskew import deskew_image
    deskewed = deskew_image(region_pil)
    save_path_deskew = rf"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page3_region{idx+1}_deskewed.png"
    deskewed.save(save_path_deskew)
    print(f"  Saved deskewed: page3_region{idx+1}_deskewed.png")
    
    # Try all 4 rotations
    for angle in [0, 90, 270]:
        rotated = deskewed.rotate(angle, expand=True) if angle != 0 else deskewed
        
        # Preprocess
        prep = rotated.convert('L')
        prep = ImageOps.autocontrast(prep)
        prep = prep.filter(ImageFilter.SHARPEN)
        
        # Save preprocessed
        save_prep = rf"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page3_region{idx+1}_rot{angle}_prep.png"
        prep.save(save_prep)
        
        # OCR
        text = pytesseract.image_to_string(prep, config='--psm 6')
        print(f"  Rotation {angle}°: {text.strip()[:50]}")

print("\n" + "=" * 60)
print("Check the saved images in artifacts folder!")
print("=" * 60)
