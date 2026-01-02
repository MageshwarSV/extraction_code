# Debug: Full OCR text on page 3 at 90 degrees
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

# Get page 3
pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

# Rotate 90 degrees (where CONSIGNMENT was found)
rotated = page.rotate(90, expand=True)

# Get full OCR text
text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')

print("=== FULL OCR TEXT (Page 3, 90 degrees) ===")
print(text)
print("\n=== ALL 5-DIGIT NUMBERS FOUND ===")
numbers = re.findall(r'\d{5}', text)
print(numbers)

print("\n=== LINES WITH 'No' or 'GC' ===")
for line in text.split('\n'):
    if 'No' in line or 'GC' in line or 'G.C' in line:
        print(f"  {line}")
