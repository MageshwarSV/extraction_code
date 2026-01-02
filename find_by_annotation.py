# Find G.C.No by annotation - get position of label then crop number
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Finding G.C.No by annotation position")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]
rotated = page.rotate(90, expand=True)

# Get word positions using image_to_data
data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

# Find words matching G.C.No variations
# Patterns: G.C.No, G.C No, GC No, C.No, C No, No.:, etc.
gc_patterns = ['G.C', 'GC', 'G', 'C.No', 'C', 'No']

print("Searching for G.C.No label...")
print("-" * 40)

gc_label_found = False
gc_box = None

for i, word in enumerate(data['text']):
    if not word:
        continue
    
    word_upper = word.upper().strip()
    
    # Check for G.C.No variations
    if any(p in word_upper for p in ['G.C', 'GC', 'C.N', 'C.NO']):
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        conf = data['conf'][i]
        print(f"  Found: '{word}' at ({x}, {y}) conf={conf}")
        gc_box = (x, y, w, h, i)
        gc_label_found = True
        
    # Also check for just "No" followed by digits
    if 'NO' in word_upper and i > 0:
        prev_word = data['text'][i-1].upper() if data['text'][i-1] else ''
        if 'C' in prev_word or 'G' in prev_word:
            x, y = data['left'][i], data['top'][i]
            print(f"  Found 'No' after '{prev_word}' at ({x}, {y})")

# If found G.C label, look for number after it
if gc_box:
    x, y, w, h, idx = gc_box
    print(f"\nG.C.No label at position: ({x}, {y})")
    
    # Look for the next numeric word
    for j in range(idx + 1, min(idx + 10, len(data['text']))):
        word = data['text'][j]
        if word and any(c.isdigit() for c in word):
            number = re.sub(r'\D', '', word)  # Extract only digits
            if len(number) >= 4:
                print(f"  Number found: {number}")
                
                # Crop the number region
                nx, ny, nw, nh = data['left'][j], data['top'][j], data['width'][j], data['height'][j]
                pad = 10
                region = rotated.crop((nx-pad, ny-pad, nx+nw+pad, ny+nh+pad))
                region.save(f"{save_dir}\\gc_number_region.png")
                print(f"  Saved gc_number_region.png")
                break
else:
    print("\nG.C.No label not found directly. Searching for 5-digit numbers...")
    for i, word in enumerate(data['text']):
        if word:
            digits = re.sub(r'\D', '', word)
            if len(digits) == 5:
                x, y = data['left'][i], data['top'][i]
                print(f"  5-digit: {digits} at ({x}, {y})")

print("\n" + "=" * 60)
