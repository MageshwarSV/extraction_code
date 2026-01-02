# Find G.C.No number after the label
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Finding G.C.No number")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]
rotated = page.rotate(90, expand=True)

# Get word positions
data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

# Find GC. or G.C position
gc_idx = None
gc_x, gc_y = None, None

for i, word in enumerate(data['text']):
    if not word:
        continue
    word_upper = word.upper().strip()
    
    if 'GC' in word_upper or 'G.C' in word_upper:
        gc_idx = i
        gc_x = data['left'][i]
        gc_y = data['top'][i]
        gc_w = data['width'][i]
        gc_h = data['height'][i]
        print(f"Found '{word}' at ({gc_x}, {gc_y}) size {gc_w}x{gc_h}")
        break

if gc_idx:
    # Look for number on same line (similar Y coordinate, X to the right)
    print(f"\nLooking for number near Y={gc_y}...")
    
    for i, word in enumerate(data['text']):
        if not word:
            continue
        
        word_y = data['top'][i]
        word_x = data['left'][i]
        
        # Must be on similar Y (within 50 pixels) and to the right
        if abs(word_y - gc_y) < 80 and word_x > gc_x:
            digits = re.sub(r'\D', '', word)
            if len(digits) >= 4:
                print(f"  Candidate: '{word}' -> digits: {digits} at ({word_x}, {word_y})")

    # Also crop the region to the right of GC label
    print(f"\nCropping region after GC label...")
    crop_x1 = gc_x + gc_w
    crop_y1 = gc_y - 30
    crop_x2 = min(rotated.width, gc_x + gc_w + 200)
    crop_y2 = gc_y + gc_h + 30
    
    number_region = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    number_region.save(f"{save_dir}\\gc_number_crop.png")
    
    # Enhance and OCR
    gray = ImageOps.grayscale(number_region)
    gray = ImageOps.autocontrast(gray)
    gray.save(f"{save_dir}\\gc_number_crop_gray.png")
    
    # OCR with digit whitelist
    text = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789', lang='eng')
    digits = re.sub(r'\D', '', text)
    print(f"OCR result: '{text.strip()}' -> digits: {digits}")

print("\n" + "=" * 60)
