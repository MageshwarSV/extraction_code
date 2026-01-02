# Debug: Check what's in the cropped region for page 1
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps
import cv2
import numpy as np

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Debug GC extraction - Page 1")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
page = pages[0]
rotated = page.rotate(90, expand=True)

data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

# Find G.C.No
gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    if re.match(r'^G\.?C\.?N', word.upper()) or word.upper().startswith('G.C'):
        gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i], 'word': word}
        print(f"Found: '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
        break

if gc_pos:
    # Large margins
    top_margin = 120
    bottom_margin = 80
    left_margin = 50
    right_extend = 700
    
    crop_x1 = max(0, gc_pos['x'] - left_margin)
    crop_y1 = max(0, gc_pos['y'] - top_margin)
    crop_x2 = min(rotated.width, gc_pos['x'] + gc_pos['w'] + right_extend)
    crop_y2 = min(rotated.height, gc_pos['y'] + gc_pos['h'] + bottom_margin)
    
    gc_region = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    gc_region.save(f"{save_dir}\\debug_page1_crop.png")
    print(f"Saved crop: ({crop_x2-crop_x1}x{crop_y2-crop_y1})")
    
    # Binarize
    img_np = np.array(gc_region)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) < 128:
        binary = cv2.bitwise_not(binary)
    
    cv2.imwrite(f"{save_dir}\\debug_page1_binary.png", binary)
    
    # OCR on binary
    from PIL import Image
    binary_pil = Image.fromarray(binary)
    
    print("\nOCR results:")
    for psm in [7, 6, 8, 11, 3]:
        text = pytesseract.image_to_string(binary_pil, config=f'--psm {psm}', lang='eng')
        text = text.strip().replace('\n', ' ')
        print(f"  PSM {psm}: {text[:80]}")
        
        # Look for any 4-6 digit numbers
        matches = re.findall(r'\d{4,6}', text)
        if matches:
            print(f"    -> Numbers found: {matches}")
            
print("=" * 60)
