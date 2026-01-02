# Test OCR directly on user's uploaded crop images
import pytesseract
from PIL import Image, ImageOps
import cv2
import numpy as np
import re
import os

save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

# User uploaded images that look clear
user_images = [
    "uploaded_image_0_1766600505138.png",  # 14549
    "uploaded_image_1_1766600505138.png",  # 14516
    "uploaded_image_2_1766600505138.png",  # 14531
    "uploaded_image_3_1766600505138.png",  # 14144
    "uploaded_image_4_1766600505138.png",  # 14512
]

print("OCR on user's uploaded crop images")
print("=" * 60)

for img_name in user_images:
    img_path = os.path.join(save_dir, img_name)
    if not os.path.exists(img_path):
        print(f"{img_name}: NOT FOUND")
        continue
    
    img = Image.open(img_path)
    print(f"\n{img_name} ({img.size}):")
    
    # Try different preprocessing
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray)
    
    # Binarize
    img_np = np.array(gray)
    _, binary = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) < 128:
        binary = cv2.bitwise_not(binary)
    binary_pil = Image.fromarray(binary)
    
    # Try PSM 7 (single line)
    for psm in [7, 6, 8, 11]:
        text = pytesseract.image_to_string(binary_pil, config=f'--psm {psm}', lang='eng')
        text = text.strip()
        
        no_spaces = text.replace(' ', '').replace('\n', '')
        match = re.search(r'(\d{5})', no_spaces)
        
        if match:
            print(f"  PSM {psm}: '{text}' -> FOUND: {match.group(1)}")
            break
        elif text:
            print(f"  PSM {psm}: '{text}'")

print("\n" + "=" * 60)
