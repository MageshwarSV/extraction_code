# Tighter crop - focus on G.C.No box area only
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Tight Crop Test - Focus on G.C.No box only")
print("=" * 60)

# Test on page 5 (failing page with clear image)
pages = convert_from_path(pdf_path, dpi=200, first_page=5, last_page=5)
page = pages[0]
rotated = page.rotate(90, expand=True)

# Find G.C.No
data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    if re.match(r'^G\.?C\.?N', word.upper()):
        gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i], 'word': word}
        print(f"Found: '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
        break

if gc_pos:
    # TIGHT CROP - just the G.C.No line
    top_margin = 30
    bottom_margin = 30
    left_margin = 20
    right_extend = 300  # Just enough for the number
    
    crop_x1 = max(0, gc_pos['x'] - left_margin)
    crop_y1 = max(0, gc_pos['y'] - top_margin)
    crop_x2 = min(rotated.width, gc_pos['x'] + gc_pos['w'] + right_extend)
    crop_y2 = min(rotated.height, gc_pos['y'] + gc_pos['h'] + bottom_margin)
    
    tight_crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    tight_crop.save(f"{save_dir}\\page5_tight_crop.png")
    print(f"Saved tight crop: {tight_crop.size}")
    
    # OCR
    gray = ImageOps.grayscale(tight_crop)
    gray = ImageOps.autocontrast(gray)
    gray.save(f"{save_dir}\\page5_tight_gray.png")
    
    text = pytesseract.image_to_string(gray, config='--psm 7', lang='eng')
    print(f"OCR: {text.strip()}")
    
    # Extract number
    no_spaces = text.replace(' ', '')
    match = re.search(r'(\d{5})', no_spaces)
    if match:
        print(f"SUCCESS: {match.group(1)}")

print("=" * 60)
