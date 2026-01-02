# Save cropped GC regions for all consignment pages
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
import os

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\gc_crops"

os.makedirs(save_dir, exist_ok=True)

print(f"Saving cropped GC regions to: {save_dir}")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=150)

for page_num, page in enumerate(pages, 1):
    rotated = page.rotate(90, expand=True)
    
    # Check if consignment page
    text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    if 'CONSIGNMENT' not in text.upper():
        continue
    
    # Find G.C.No label
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper().strip()
        if len(word) < 15 and '@' not in word:
            if re.match(r'^G\.?C\.?N', word_upper) or re.match(r'^[56S]\.?C\.?N', word_upper):
                gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i], 'word': word}
                break
    
    if gc_pos:
        # Large margins
        top_margin = 150
        bottom_margin = 100
        left_margin = 60
        right_extend = 800
        
        crop_x1 = max(0, gc_pos['x'] - left_margin)
        crop_y1 = max(0, gc_pos['y'] - top_margin)
        crop_x2 = min(rotated.width, gc_pos['x'] + gc_pos['w'] + right_extend)
        crop_y2 = min(rotated.height, gc_pos['y'] + gc_pos['h'] + bottom_margin)
        
        gc_region = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        # Save
        save_path = f"{save_dir}\\page{page_num}_gc_crop.png"
        gc_region.save(save_path)
        print(f"Page {page_num}: Saved (label: '{gc_pos['word']}')")
    else:
        print(f"Page {page_num}: No G.C.No label found")

print("=" * 60)
print(f"All crops saved to: {save_dir}")
