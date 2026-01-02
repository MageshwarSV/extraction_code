# Find ALL G.C.No labels on failing pages (not just first one)
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Find ALL G.C.No labels on failing pages")
print("=" * 60)

for page_num in [3, 5, 17]:
    print(f"\n=== Page {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    print("  ALL G.C related words:")
    gc_labels = []
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper()
        
        # Match any G.C pattern
        if 'G.C' in word_upper or 'GC' in word_upper or 'C.NO' in word_upper:
            x = data['left'][i]
            y = data['top'][i]
            gc_labels.append({'x': x, 'y': y, 'word': word, 'idx': i})
            print(f"    '{word}' at ({x}, {y})")
    
    # For each G.C label, show nearby digits
    for gc in gc_labels:
        print(f"\n  Digits near '{gc['word']}' (Y={gc['y']}):")
        for i, word in enumerate(data['text']):
            if not word:
                continue
            digits = re.sub(r'\D', '', word)
            if not digits:
                continue
            
            word_x = data['left'][i]
            word_y = data['top'][i]
            
            # Within 300px X and 100px Y
            if gc['x'] - 100 < word_x < gc['x'] + 500:
                if abs(word_y - gc['y']) < 100:
                    print(f"      '{word}' -> digits='{digits}' at ({word_x}, {word_y})")

print("\n" + "=" * 60)
