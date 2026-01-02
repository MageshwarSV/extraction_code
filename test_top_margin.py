# Try larger TOP margin to capture tilted digits
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps
import os

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Test VERY LARGE top margin for tilted numbers")
print("=" * 60)

# Test multiple pages with different top margins
for page_num in [1, 3, 5]:
    print(f"\n=== Page {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        if re.match(r'^G\.?C\.?N', word.upper()):
            gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
            break
    
    if not gc_pos:
        print("  G.C.No label not found")
        continue
    
    # Try different top margins
    for top_margin in [50, 100, 150, 200, 250]:
        crop_x1 = max(0, gc_pos['x'] - 50)
        crop_y1 = max(0, gc_pos['y'] - top_margin)  # VARY THIS
        crop_x2 = min(rotated.width, gc_pos['x'] + gc_pos['w'] + 400)
        crop_y2 = min(rotated.height, gc_pos['y'] + gc_pos['h'] + 80)
        
        crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        gray = ImageOps.grayscale(crop)
        gray = ImageOps.autocontrast(gray)
        
        text = pytesseract.image_to_string(gray, config='--psm 6', lang='eng')
        no_spaces = text.replace(' ', '').replace('\n', '')
        
        match = re.search(r'(\d{5})', no_spaces)
        if match:
            print(f"  Top margin {top_margin}px: FOUND {match.group(1)}")
            break
        else:
            # Show what was found
            digits = re.findall(r'\d+', text)
            print(f"  Top margin {top_margin}px: digits={digits}")

print("\n" + "=" * 60)
