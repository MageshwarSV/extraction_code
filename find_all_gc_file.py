# Find ALL G.C.No labels on failing pages - write to file
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\gc_debug.txt"

with open(output_path, 'w') as f:
    f.write("Find ALL G.C.No labels on failing pages\n")
    f.write("=" * 60 + "\n")
    
    for page_num in [3, 5, 17]:
        f.write(f"\n=== Page {page_num} ===\n")
        
        pages = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
        page = pages[0]
        rotated = page.rotate(90, expand=True)
        
        data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
        
        f.write("  ALL G.C related words:\n")
        gc_labels = []
        for i, word in enumerate(data['text']):
            if not word:
                continue
            word_upper = word.upper()
            
            if 'G.C' in word_upper or 'GC' in word_upper or 'C.NO' in word_upper:
                x = data['left'][i]
                y = data['top'][i]
                gc_labels.append({'x': x, 'y': y, 'word': word, 'idx': i})
                f.write(f"    '{word}' at ({x}, {y})\n")
        
        for gc in gc_labels:
            f.write(f"\n  Digits near '{gc['word']}' (Y={gc['y']}):\n")
            for i, word in enumerate(data['text']):
                if not word:
                    continue
                digits = re.sub(r'\D', '', word)
                if not digits:
                    continue
                
                word_x = data['left'][i]
                word_y = data['top'][i]
                
                if gc['x'] - 100 < word_x < gc['x'] + 500:
                    if abs(word_y - gc['y']) < 100:
                        f.write(f"      '{word}' -> digits='{digits}' at ({word_x}, {word_y})\n")
    
    f.write("\n" + "=" * 60 + "\n")

print(f"Debug output saved to: {output_path}")
