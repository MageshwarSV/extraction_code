# Correct crop - number is BELOW the label (in rotated view)
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("GC Extraction - Number Below Label")
print("=" * 60)

# Fast scan at 150 DPI
print("\n1. Fast scan to find G.C.No label...")
pages_low = convert_from_path(pdf_path, dpi=150, first_page=3, last_page=3)
page_low = pages_low[0]
rotated_low = page_low.rotate(90, expand=True)

data = pytesseract.image_to_data(rotated_low, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    word_upper = word.upper()
    
    if 'G.C' in word_upper or 'GC' in word_upper or 'C.NO' in word_upper:
        gc_pos = {
            'x': data['left'][i],
            'y': data['top'][i],
            'w': data['width'][i],
            'h': data['height'][i]
        }
        print(f"   Found '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
        break

if gc_pos:
    # Scale to 300 DPI
    scale = 2.0  # 300/150
    gc_x = int(gc_pos['x'] * scale)
    gc_y = int(gc_pos['y'] * scale)
    gc_h = int(gc_pos['h'] * scale)
    
    # Get high res image
    pages_high = convert_from_path(pdf_path, dpi=300, first_page=3, last_page=3)
    rotated_high = pages_high[0].rotate(90, expand=True)
    
    # The number is BELOW the label in rotated view
    # So we crop: same X, but Y below the label
    print(f"\n2. Cropping number region (below label)...")
    
    # Crop region BELOW the label (Y increases going down)
    crop_x1 = gc_x - 20
    crop_y1 = gc_y + gc_h  # Start after the label
    crop_x2 = gc_x + 300   # Wide enough for number
    crop_y2 = gc_y + gc_h + 200  # Height for number
    
    # Make sure bounds are valid
    crop_x1 = max(0, crop_x1)
    crop_y1 = max(0, crop_y1)
    crop_x2 = min(rotated_high.width, crop_x2)
    crop_y2 = min(rotated_high.height, crop_y2)
    
    number_region = rotated_high.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    number_region.save(f"{save_dir}\\gc_number_below.png")
    print(f"   Saved gc_number_below.png")
    
    # OCR
    gray = ImageOps.grayscale(number_region)
    gray = ImageOps.autocontrast(gray)
    gray.save(f"{save_dir}\\gc_number_below_gray.png")
    
    print(f"\n3. OCR on number region...")
    text = pytesseract.image_to_string(gray, config='--psm 6', lang='eng')
    print(f"   Full OCR: {text.strip()}")
    
    # Try digit-only
    text_digits = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789', lang='eng')
    digits = re.sub(r'\D', '', text_digits)
    print(f"   Digits: {digits}")
    
    if digits and len(digits) >= 4:
        print(f"\n   ✓ G.C.No.: {digits}")
    else:
        print(f"\n   Trying different crop (left of label)...")
        # Maybe number is to the LEFT
        crop_x1_left = gc_x - 200
        crop_x2_left = gc_x - 10
        crop_y1_left = gc_y - 20
        crop_y2_left = gc_y + gc_h + 20
        
        left_region = rotated_high.crop((max(0, crop_x1_left), max(0, crop_y1_left), 
                                         min(rotated_high.width, crop_x2_left), 
                                         min(rotated_high.height, crop_y2_left)))
        left_region.save(f"{save_dir}\\gc_number_left.png")
        
        gray_left = ImageOps.grayscale(left_region)
        gray_left = ImageOps.autocontrast(gray_left)
        
        text_left = pytesseract.image_to_string(gray_left, config='--psm 7 -c tessedit_char_whitelist=0123456789', lang='eng')
        digits_left = re.sub(r'\D', '', text_left)
        print(f"   Left region digits: {digits_left}")

print("\n" + "=" * 60)
