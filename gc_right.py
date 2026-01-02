# Number is to the RIGHT of G.C.No on same line
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("GC Extract - Number to RIGHT of label (same line)")
print("=" * 60)

# Fast scan
pages_low = convert_from_path(pdf_path, dpi=150, first_page=3, last_page=3)
rotated_low = pages_low[0].rotate(90, expand=True)

data = pytesseract.image_to_data(rotated_low, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    if 'G.C' in word.upper() or 'GC' in word.upper():
        gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
        print(f"Found '{word}' at x={gc_pos['x']}, y={gc_pos['y']}, w={gc_pos['w']}")
        break

if gc_pos:
    # Scale to 300 DPI
    scale = 2.0
    gc_x = int(gc_pos['x'] * scale)
    gc_y = int(gc_pos['y'] * scale)
    gc_w = int(gc_pos['w'] * scale)
    gc_h = int(gc_pos['h'] * scale)
    
    # High res
    pages_high = convert_from_path(pdf_path, dpi=300, first_page=3, last_page=3)
    rotated_high = pages_high[0].rotate(90, expand=True)
    
    # Crop to the RIGHT of the label (same Y, X after label ends)
    # Include the whole line with G.C.No.: 14511
    crop_x1 = gc_x - 20  # Start a bit before label
    crop_y1 = gc_y - 20  # Same Y
    crop_x2 = gc_x + gc_w + 400  # Extend far right for the number
    crop_y2 = gc_y + gc_h + 20  # Same height
    
    # Ensure valid bounds
    crop_x1 = max(0, crop_x1)
    crop_y1 = max(0, crop_y1)
    crop_x2 = min(rotated_high.width, crop_x2)
    crop_y2 = min(rotated_high.height, crop_y2)
    
    full_line = rotated_high.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    full_line.save(f"{save_dir}\\gc_full_line.png")
    print(f"\nSaved gc_full_line.png (full G.C.No.: XXXXX line)")
    
    # OCR
    gray = ImageOps.grayscale(full_line)
    gray = ImageOps.autocontrast(gray)
    gray.save(f"{save_dir}\\gc_full_line_gray.png")
    
    text = pytesseract.image_to_string(gray, config='--psm 7', lang='eng')
    print(f"OCR: {text.strip()}")
    
    # Extract number
    match = re.search(r'(\d{4,6})', text)
    if match:
        print(f"\n✓ G.C.No.: {match.group(1)}")
    else:
        # Crop ONLY the number part (right side)
        num_x1 = gc_x + gc_w + 20
        num_region = rotated_high.crop((num_x1, crop_y1, crop_x2, crop_y2))
        num_region.save(f"{save_dir}\\gc_number_only.png")
        
        text2 = pytesseract.image_to_string(ImageOps.autocontrast(ImageOps.grayscale(num_region)), 
                                            config='--psm 7 -c tessedit_char_whitelist=0123456789', lang='eng')
        digits = re.sub(r'\D', '', text2)
        print(f"Number only: {digits}")

print("=" * 60)
