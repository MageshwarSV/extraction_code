# Debug OCR on saved crop images
import pytesseract
from PIL import Image, ImageOps
import cv2
import numpy as np
import re

save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\gc_crops"

print("OCR Debug on saved crops")
print("=" * 60)

for page_num in [1, 3, 5, 9, 12, 13, 17, 19]:
    img_path = f"{save_dir}\\page{page_num}_gc_crop.png"
    try:
        img = Image.open(img_path)
    except:
        continue
    
    print(f"\nPage {page_num}:")
    print("-" * 40)
    
    # Grayscale + autocontrast
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray)
    
    # Binarize
    img_np = np.array(gray)
    _, binary = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) < 128:
        binary = cv2.bitwise_not(binary)
    binary_pil = Image.fromarray(binary)
    
    # OCR both
    for name, im in [("gray", gray), ("binary", binary_pil)]:
        text = pytesseract.image_to_string(im, config='--psm 6', lang='eng')
        text_clean = text.replace('\n', ' ').strip()
        
        # Find 5-digit after removing spaces
        no_spaces = text.replace(' ', '').replace('\n', '')
        match = re.search(r'(\d{5})', no_spaces)
        
        print(f"  {name}: {text_clean[:60]}...")
        if match:
            print(f"       -> FOUND: {match.group(1)}")

print("\n" + "=" * 60)
