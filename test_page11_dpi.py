# Test different DPI and PSM modes for Page 11
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("=" * 70)
print("PAGE 11 - TESTING DIFFERENT DPI AND PSM")
print("=" * 70)

for dpi in [200, 300, 400]:
    print(f"\n\nDPI: {dpi}")
    print("-" * 40)
    
    pages = convert_from_path(pdf_path, dpi=dpi, first_page=11, last_page=11)
    page = pages[0]
    
    for psm in [6, 3, 4]:
        text = pytesseract.image_to_string(page, config=f'--psm {psm}', lang='eng')
        
        # Find vehicle line
        for line in text.split('\n'):
            if 'vehicle' in line.lower():
                print(f"  PSM {psm}: {line[:60]}")
                break
        else:
            # Try to find AP39 pattern
            match = re.search(r'AP39[A-Z0-9]*', text, re.IGNORECASE)
            if match:
                print(f"  PSM {psm}: Found AP39 pattern: {match.group()}")
