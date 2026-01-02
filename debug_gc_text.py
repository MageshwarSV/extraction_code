# Debug: See what OCR text looks like on consignment pages
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

# Get page 3 (known consignment page)
pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

# Try all rotations
rotations = [0, 90, 270, 180]

for angle in rotations:
    if angle == 0:
        rotated = page
    else:
        rotated = page.rotate(angle, expand=True)
    
    text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    
    if 'CONSIGNMENT' in text.upper():
        print(f"\n=== ROTATION {angle} (Found CONSIGNMENT) ===")
        print(text[:1000])
        print("\n=== Looking for G.C.No pattern ===")
        for line in text.split('\n'):
            if 'G' in line and 'C' in line and 'N' in line.upper():
                print(f"  Possible match: {line}")
        break
