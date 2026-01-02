# Save all GC number crops for manual verification
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

print(f"Saving GC number crops to: {save_dir}")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=300)

consignment_pages = []

for page_num, page in enumerate(pages, 1):
    rotated = page.rotate(90, expand=True)
    
    # Check if consignment
    text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    if 'CONSIGNMENT' not in text.upper():
        continue
    
    consignment_pages.append(page_num)
    
    # Find G.C.No
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        if 'G.C' in word.upper() or 'GC' in word.upper():
            gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
            break
    
    if gc_pos:
        # Crop the number region
        crop_x1 = gc_pos['x'] + gc_pos['w'] - 50
        crop_y1 = gc_pos['y'] - 50
        crop_x2 = min(rotated.width, gc_pos['x'] + gc_pos['w'] + 500)
        crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
        
        crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        # Save
        save_path = f"{save_dir}\\page{page_num:02d}_gc.png"
        crop.save(save_path)
        print(f"Page {page_num}: Saved crop ({crop.size[0]}x{crop.size[1]})")
    else:
        print(f"Page {page_num}: No G.C.No label found")

print("=" * 60)
print(f"Saved {len(consignment_pages)} crops to: {save_dir}")
print(f"Consignment pages: {consignment_pages}")
