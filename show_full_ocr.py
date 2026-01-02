# Show full OCR at 90 degrees to find where G.C.No is
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]
rotated = page.rotate(90, expand=True)

text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')

print("Full OCR at 90 degrees:")
print("=" * 60)
print(text)
print("=" * 60)

# Look for any line with "G" and "C" and "N"
print("\nLines with G, C, N:")
for line in text.split('\n'):
    if 'G' in line and 'C' in line and 'N' in line.upper():
        print(f"  {line}")
