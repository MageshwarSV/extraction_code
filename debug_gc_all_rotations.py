# Debug: Try all rotations and look for G.C.No pattern specifically
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

# Get page 3
pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

print("Looking for G.C.No in all 4 rotations...\n")

# Try all rotations
for angle in [0, 90, 180, 270]:
    if angle == 0:
        rotated = page
    else:
        rotated = page.rotate(angle, expand=True)
    
    # Get full OCR text
    text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    
    # Look for any 5-digit numbers
    numbers = re.findall(r'\d{5}', text)
    
    # Look for G.C related patterns
    gc_lines = [line for line in text.split('\n') if 'G' in line and 'C' in line and any(c.isdigit() for c in line)]
    
    print(f"=== {angle}° ===")
    print(f"  5-digit numbers: {numbers[:5] if numbers else 'None'}")
    print(f"  Lines with G,C and digits: {len(gc_lines)}")
    
    # Try PSM 11 (sparse text)
    text2 = pytesseract.image_to_string(rotated, config='--psm 11', lang='eng')
    numbers2 = re.findall(r'\d{5}', text2)
    print(f"  PSM 11 - 5-digit numbers: {numbers2[:5] if numbers2 else 'None'}")
    
    if gc_lines:
        for line in gc_lines[:3]:
            print(f"    {line}")
