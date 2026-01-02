# Debug pages 5, 17, 19 - show all words containing G or C in top 45%
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Debug pages 5, 17, 19 - find G.C.No patterns")
print("=" * 60)

for page_num in [5, 17, 19]:
    print(f"\n=== Page {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    # Top 45%
    top_height = int(rotated.height * 0.45)
    top_region = rotated.crop((0, 0, rotated.width, top_height))
    
    data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    print("  Words containing 'G' or 'C' or 'No':")
    for i, word in enumerate(data['text']):
        if not word:
            continue
        word_upper = word.upper()
        
        # Show any word that might be G.C.No related
        if 'G.' in word or 'C.' in word or 'GC' in word_upper or 'NO' in word_upper:
            if len(word) < 20:
                x = data['left'][i]
                y = data['top'][i]
                print(f"    '{word}' at ({x}, {y})")

print("\n" + "=" * 60)
