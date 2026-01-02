# Final crop script - includes OCR error patterns
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import os
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"

os.makedirs(save_dir, exist_ok=True)

print(f"Saving GC crops (with OCR error handling)")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=300)

for page_num, page in enumerate(pages, 1):
    rotated = page.rotate(90, expand=True)
    
    text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    if 'CONSIGNMENT' not in text.upper():
        continue
    
    # Top 50% (slightly larger)
    top_region_height = int(rotated.height * 0.50)
    top_region = rotated.crop((0, 0, rotated.width, top_region_height))
    
    data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper().strip()
        
        # Various G.C.No patterns including OCR errors
        patterns = [
            r'G\.?C\.?N',      # G.C.No, GCNo, G.CN
            r'5\.?C\.?N',      # 5.C.N (G misread as 5)
            r'6\.?C\.?N',      # 6.C.N (G misread as 6)
            r'[;,\.]\.?N[Oo]', # ;.No (G.C misread as ;.)
        ]
        
        for pattern in patterns:
            if re.search(pattern, word_upper):
                gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i], 'word': word}
                break
        
        if gc_pos:
            break
    
    if gc_pos:
        print(f"Page {page_num}: Found '{gc_pos['word']}' at ({gc_pos['x']}, {gc_pos['y']})")
        
        crop_x1 = gc_pos['x'] + gc_pos['w'] - 50
        crop_y1 = gc_pos['y'] - 50
        crop_x2 = min(top_region.width, gc_pos['x'] + gc_pos['w'] + 500)
        crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
        
        crop = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        save_path = f"{save_dir}\\page{page_num:02d}_gc.png"
        crop.save(save_path)
        print(f"  Saved: {crop.size[0]}x{crop.size[1]}")
    else:
        print(f"Page {page_num}: No G.C.No label found")

print("=" * 60)
print(f"Done! Check: {save_dir}")
