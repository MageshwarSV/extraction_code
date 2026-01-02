# Debug page 7 - save to file
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"
output_path = f"{save_dir}\\page7_debug.txt"

with open(output_path, 'w') as f:
    f.write("Debug Page 7 - Expected: 14519\n")
    f.write("=" * 60 + "\n\n")
    
    pages = convert_from_path(pdf_path, dpi=200, first_page=7, last_page=7)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    f.write("G.C related words:\n")
    for i, word in enumerate(data['text']):
        if not word:
            continue
        if 'G.C' in word.upper() or 'GC' in word.upper():
            f.write(f"  '{word}' at ({data['left'][i]}, {data['top'][i]})\n")
    
    f.write("\nAll words with digits:\n")
    for i, word in enumerate(data['text']):
        if not word:
            continue
        digits = re.sub(r'\D', '', word)
        if len(digits) >= 2:
            f.write(f"  '{word}' -> '{digits}' at ({data['left'][i]}, {data['top'][i]})\n")
    
    # Full text
    full_text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    no_spaces = full_text.replace(' ', '').replace('\n', '')
    
    f.write("\n5-digit numbers starting with 1:\n")
    matches = re.findall(r'1\d{4}', no_spaces)
    f.write(f"  {matches}\n")
    
    f.write("\nFirst 500 chars of full text:\n")
    f.write(full_text[:500].replace('\n', ' | ') + "\n")

print(f"Debug saved to: {output_path}")
