# Fast preprocess to find GC location, then crop for number
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Fast GC Detection + Crop Extraction")
print("=" * 60)

# STEP 1: Fast preprocess at LOW DPI (150) to find GC position
print("\n1. Fast scan at 150 DPI to find GC label...")
pages_low = convert_from_path(pdf_path, dpi=150, first_page=3, last_page=3)
page_low = pages_low[0]
rotated_low = page_low.rotate(90, expand=True)

# Get word positions - looking for GC variations
data = pytesseract.image_to_data(rotated_low, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_found = False
gc_pos = None

# Search for GC, G C, G.C, G. C, C.No, C No, etc.
gc_patterns = ['GC', 'G.C', 'C.N', 'C.NO', 'G.', 'G ']

for i, word in enumerate(data['text']):
    if not word:
        continue
    
    word_upper = word.upper().strip()
    
    # Check if matches any GC pattern
    for pattern in gc_patterns:
        if pattern in word_upper:
            gc_pos = {
                'word': word,
                'x': data['left'][i],
                'y': data['top'][i],
                'w': data['width'][i],
                'h': data['height'][i],
                'idx': i
            }
            print(f"   FOUND: '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
            gc_found = True
            break
    
    if gc_found:
        break

if not gc_found:
    print("   GC label not found!")
else:
    # STEP 2: Scale up coordinates for HIGH DPI extraction
    low_dpi = 150
    high_dpi = 300
    scale = high_dpi / low_dpi
    
    print(f"\n2. Converting coordinates for {high_dpi} DPI...")
    gc_x_high = int(gc_pos['x'] * scale)
    gc_y_high = int(gc_pos['y'] * scale)
    
    print(f"   GC position at {high_dpi} DPI: ({gc_x_high}, {gc_y_high})")
    
    # STEP 3: Get HIGH DPI image and crop the GC number region
    print(f"\n3. Getting {high_dpi} DPI image and cropping number region...")
    pages_high = convert_from_path(pdf_path, dpi=high_dpi, first_page=3, last_page=3)
    page_high = pages_high[0]
    rotated_high = page_high.rotate(90, expand=True)
    
    # The number is BELOW the "G.C.No.:" label in the original image
    # After rotating 90°, "below" becomes "to the right"
    # Crop a region starting from GC position, extending down (right after rotation)
    crop_x1 = gc_x_high
    crop_y1 = gc_y_high - 20
    crop_x2 = gc_x_high + 400  # Wide enough for "G.C.No.: 14511"
    crop_y2 = gc_y_high + 100  # Tall enough
    
    gc_region = rotated_high.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    gc_region.save(f"{save_dir}\\gc_region_wide.png")
    print(f"   Saved gc_region_wide.png")
    
    # STEP 4: OCR on cropped region only
    print(f"\n4. OCR on cropped region...")
    gray = ImageOps.grayscale(gc_region)
    gray = ImageOps.autocontrast(gray)
    gray.save(f"{save_dir}\\gc_region_wide_gray.png")
    
    # Full OCR on small region
    text = pytesseract.image_to_string(gray, config='--psm 6', lang='eng')
    print(f"   OCR: {text.strip()}")
    
    # Extract number
    gc_match = re.search(r'(\d{4,6})', text)
    if gc_match:
        print(f"\n   ✓ G.C.No.: {gc_match.group(1)}")
    else:
        # Try digit-only OCR
        text_digits = pytesseract.image_to_string(gray, config='--psm 7 -c tessedit_char_whitelist=0123456789', lang='eng')
        digits = re.sub(r'\D', '', text_digits)
        if digits:
            print(f"\n   ✓ G.C.No. (digits): {digits}")
        else:
            print(f"\n   ✗ Number not extracted")

print("\n" + "=" * 60)
