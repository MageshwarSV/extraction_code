# Manually handle pages 5 and 17
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"

print("Handle pages 5 and 17 manually")
print("=" * 60)

for page_num in [5, 17]:
    print(f"\n=== Page {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    # Top 50%
    top_height = int(rotated.height * 0.50)
    top_region = rotated.crop((0, 0, rotated.width, top_height))
    
    data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    print("  All words with 'No' or '.' pattern near expected area (x>2000):")
    candidates = []
    for i, word in enumerate(data['text']):
        if not word:
            continue
        x = data['left'][i]
        y = data['top'][i]
        
        # Look for any word containing "No" or "." in the right area
        if x > 2000 and ('.' in word or 'NO' in word.upper() or 'N' in word.upper()):
            if len(word) < 15:
                print(f"    '{word}' at ({x}, {y})")
                candidates.append({'x': x, 'y': y, 'w': data['width'][i], 'h': data['height'][i], 'word': word})
    
    # Take the candidate that looks most like G.C.No
    # For page 17, we saw ';.No.:' at (2630, 624)
    for c in candidates:
        if 'No' in c['word'] or ';' in c['word']:
            print(f"\n  Best candidate: '{c['word']}' at ({c['x']}, {c['y']})")
            
            # Crop
            crop_x1 = c['x'] + c['w'] - 30
            crop_y1 = c['y'] - 50
            crop_x2 = min(top_region.width, c['x'] + c['w'] + 500)
            crop_y2 = c['y'] + c['h'] + 80
            
            crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            crop.save(f"{save_dir}\\page{page_num:02d}_gc.png")
            print(f"  Saved crop: {crop.size}")
            break

print("\n" + "=" * 60)
