# Save crops for failing pages 3, 5, 17 to inspect
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

print("Saving crops for failing pages 3, 5, 17")
print("=" * 60)

for page_num in [3, 5, 17]:
    print(f"\n=== Page {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    # Save full rotated page
    rotated.save(f"{save_dir}\\fail_page{page_num}_full.png")
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    # Find G.C.No
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        if 'G.C' in word.upper() or 'GC' in word.upper():
            gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i], 'word': word}
            print(f"  G.C.No: '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
            break
    
    if gc_pos:
        # Large crop
        top_margin = 200
        bottom_margin = 150
        left_margin = 50
        right_extend = 800
        
        crop_x1 = max(0, gc_pos['x'] - left_margin)
        crop_y1 = max(0, gc_pos['y'] - top_margin)
        crop_x2 = min(rotated.width, gc_pos['x'] + gc_pos['w'] + right_extend)
        crop_y2 = min(rotated.height, gc_pos['y'] + gc_pos['h'] + bottom_margin)
        
        crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        crop.save(f"{save_dir}\\fail_page{page_num}_crop.png")
        print(f"  Saved crop: {crop.size}")
        
        # Binarize
        gray = ImageOps.grayscale(crop)
        img_np = np.array(gray)
        _, binary = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(binary) < 128:
            binary = cv2.bitwise_not(binary)
        cv2.imwrite(f"{save_dir}\\fail_page{page_num}_binary.png", binary)
        
        # OCR on binary
        from PIL import Image
        binary_pil = Image.fromarray(binary)
        text = pytesseract.image_to_string(binary_pil, config='--psm 6', lang='eng')
        print(f"  OCR: {text[:100].replace(chr(10), ' ')}")
        
        # Find digits
        no_spaces = text.replace(' ', '').replace('\n', '')
        match = re.search(r'1\d{4}', no_spaces)
        if match:
            print(f"  FOUND: {match.group(0)}")
        else:
            digits = re.findall(r'\d+', text)
            print(f"  Digits found: {digits}")

print("\n" + "=" * 60)
print(f"Crops saved to: {save_dir}")
