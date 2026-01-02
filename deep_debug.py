# Deep debug pages 3, 5, 17 - check both rotations
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Deep Debug Pages 3, 5, 17")
print("=" * 60)

for page_num in [3, 5, 17]:
    print(f"\n{'='*20} PAGE {page_num} {'='*20}")
    
    pages = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
    page = pages[0]
    
    for rotation in [90, 270]:
        rotated = page.rotate(rotation, expand=True)
        
        data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
        
        print(f"\n  Rotation {rotation}:")
        
        # Find G.C.No
        gc_pos = None
        for i, word in enumerate(data['text']):
            if not word:
                continue
            if 'G.C' in word.upper() or 'GC' in word.upper():
                gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'word': word}
                print(f"    G.C.No: '{word}' at ({gc_pos['x']}, {gc_pos['y']})")
                break
        
        if not gc_pos:
            print(f"    G.C.No NOT FOUND")
            continue
        
        # Show ALL words with digits to the right (extended range)
        print(f"    Words with digits to right (within 200px Y):")
        fragments = []
        for i, word in enumerate(data['text']):
            if not word:
                continue
            
            word_x = data['left'][i]
            word_y = data['top'][i]
            
            # Extended range
            if word_x > gc_pos['x'] and abs(word_y - gc_pos['y']) < 200:
                digits = re.sub(r'\D', '', word)
                if digits:
                    fragments.append((word_x, digits, word))
                    print(f"      '{word}' -> '{digits}' at ({word_x}, {word_y})")
        
        if fragments:
            fragments.sort(key=lambda x: x[0])
            combined = ''.join([f[1] for f in fragments])
            print(f"    Combined: {combined}")

print("\n" + "=" * 60)
