# Debug failing pages - show all words near G.C.No label
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Debug Failing Pages - Words near G.C.No")
print("=" * 60)

failing_pages = [3, 5, 7, 17]

for page_num in failing_pages:
    print(f"\n=== PAGE {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    # Find G.C.No label
    gc_pos = None
    gc_idx = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper().strip()
        
        if 'G.C' in word_upper or 'GC' in word_upper or re.match(r'^[56S]\.?C\.?N', word_upper):
            gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'word': word}
            gc_idx = i
            print(f"  G.C.No label: '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
            break
    
    if not gc_pos:
        print("  G.C.No label NOT FOUND!")
        # Show all words that might be G.C related
        for i, word in enumerate(data['text']):
            if word and ('G' in word.upper() or 'C' in word.upper() or 'N' in word.upper()):
                if len(word) < 15:
                    print(f"    Maybe: '{word}' at ({data['left'][i]}, {data['top'][i]})")
        continue
    
    # Show ALL words to the right of label (within Y range)
    print(f"  Words to the right (within 100px Y):")
    for i, word in enumerate(data['text']):
        if not word:
            continue
        
        word_x = data['left'][i]
        word_y = data['top'][i]
        conf = data['conf'][i]
        
        # To the right and similar Y
        if word_x > gc_pos['x'] and abs(word_y - gc_pos['y']) < 100:
            digits = re.sub(r'\D', '', word)
            if digits or any(c.isdigit() for c in word):
                print(f"    '{word}' (digits:{digits}) at ({word_x}, {word_y}) conf={conf}")

print("\n" + "=" * 60)
