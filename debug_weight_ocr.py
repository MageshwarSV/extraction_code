from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import pytesseract
import os

Image.MAX_IMAGE_PIXELS = None

# Load Page 2
pages = convert_from_path(r'DocScanner 23-Dec-2025 05-02 PM.pdf', dpi=300)
page = pages[1]  # Page 2 (0-indexed)

img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
height, width = img_cv.shape[:2]

# Crop 40-65% vertical region (product table area)
region = img_cv[int(height*0.40):int(height*0.65), :]

# Save the cropped region
debug_dir = r'gc_crops_verify/actual_weight'
os.makedirs(debug_dir, exist_ok=True)
cv2.imwrite(os.path.join(debug_dir, 'test_region.png'), region)
print("Saved test_region.png")

# OCR and print all detected words
data = pytesseract.image_to_data(region, config='--psm 6', output_type=pytesseract.Output.DICT)

print("\nAll detected words:")
for i, text in enumerate(data['text']):
    if text.strip():
        print(f"  '{text}': ({data['left'][i]}, {data['top'][i]})")
        
# Search for Qty
print("\nSearching for 'Qty' or 'MT'...")
for i, text in enumerate(data['text']):
    t = text.strip().lower()
    if 'qty' in t or t == 'mt':
        print(f"  FOUND: '{text}' at ({data['left'][i]}, {data['top'][i]})")
