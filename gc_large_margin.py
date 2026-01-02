# GC Extract - with larger margins for skewed/tilted images
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps, ImageFilter
import cv2
import numpy as np

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("GC Extract - Large margins for skewed images")
print("=" * 60)

# Fast scan
pages_low = convert_from_path(pdf_path, dpi=150, first_page=3, last_page=3)
rotated_low = pages_low[0].rotate(90, expand=True)

data = pytesseract.image_to_data(rotated_low, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    if 'G.C' in word.upper() or 'GC' in word.upper() or 'C.N' in word.upper():
        gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
        print(f"Found '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
        break

if gc_pos:
    scale = 2.0
    gc_x = int(gc_pos['x'] * scale)
    gc_y = int(gc_pos['y'] * scale)
    gc_w = int(gc_pos['w'] * scale)
    gc_h = int(gc_pos['h'] * scale)
    
    pages_high = convert_from_path(pdf_path, dpi=300, first_page=3, last_page=3)
    rotated_high = pages_high[0].rotate(90, expand=True)
    
    # LARGE MARGINS for skewed images
    # Increase TOP margin significantly
    top_margin = 80    # Much larger top margin for uphill skew
    bottom_margin = 50 # Bottom margin
    left_margin = 30   # Left margin
    right_extend = 500 # Extend far right for number
    
    crop_x1 = gc_x - left_margin
    crop_y1 = gc_y - top_margin  # Large top margin for skew
    crop_x2 = gc_x + gc_w + right_extend
    crop_y2 = gc_y + gc_h + bottom_margin
    
    # Bounds check
    crop_x1 = max(0, crop_x1)
    crop_y1 = max(0, crop_y1)
    crop_x2 = min(rotated_high.width, crop_x2)
    crop_y2 = min(rotated_high.height, crop_y2)
    
    full_line = rotated_high.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    full_line.save(f"{save_dir}\\gc_large_margin.png")
    print(f"Saved gc_large_margin.png ({full_line.size})")
    
    # Preprocessing: Convert to grayscale and binarize for better OCR
    gray = ImageOps.grayscale(full_line)
    gray = ImageOps.autocontrast(gray)
    
    # Binarization to make text clearer
    cv_img = np.array(gray)
    _, binary = cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary_pil = ImageOps.invert(ImageOps.invert(gray).point(lambda x: 0 if x < 128 else 255, '1'))
    
    # Save preprocessed
    gray.save(f"{save_dir}\\gc_large_gray.png")
    
    # OCR with different PSM modes
    print("\nOCR attempts:")
    for psm in [6, 7, 8, 11]:
        text = pytesseract.image_to_string(gray, config=f'--psm {psm}', lang='eng')
        text = text.strip()
        if text:
            match = re.search(r'(\d{4,6})', text)
            if match:
                print(f"  PSM {psm}: '{text}' -> Number: {match.group(1)}")
            else:
                print(f"  PSM {psm}: '{text}'")
    
    # Also try on binary image
    cv2.imwrite(f"{save_dir}\\gc_binary.png", binary)
    binary_text = pytesseract.image_to_string(f"{save_dir}\\gc_binary.png", config='--psm 7', lang='eng')
    print(f"  Binary: '{binary_text.strip()}'")
    
    match = re.search(r'(\d{4,6})', binary_text)
    if match:
        print(f"\n✓ G.C.No.: {match.group(1)}")

print("=" * 60)
