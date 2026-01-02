# Find the actual number position using image_to_data
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re
from PIL import ImageOps

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Find NUMBER position instead of label position")
print("=" * 60)

# Page 1
pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
page = pages[0]
rotated = page.rotate(90, expand=True)

data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

print("All detected words with positions:")
for i, word in enumerate(data['text']):
    if not word:
        continue
    
    # Show words near expected GC label
    y = data['top'][i]
    x = data['left'][i]
    conf = data['conf'][i]
    
    # Look for G.C or digits
    if 'G.' in word.upper() or 'C.' in word.upper() or any(c.isdigit() for c in word):
        print(f"  '{word}' at ({x}, {y}) conf={conf}")
        
        # If this contains 4-5 digits, note the Y position
        if re.search(r'\d{4,5}', word):
            print(f"    ^ NUMBER FOUND at Y={y}")

print("=" * 60)
