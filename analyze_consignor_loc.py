# Analyze Consignor location
import sys
import os
sys.path.insert(0, os.getcwd())

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.deskew import deskew_and_enhance

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
pages = convert_from_path(pdf_path, dpi=300, first_page=2, last_page=2)
page = pages[0]
page_corrected = deskew_and_enhance(page)

# OCR with PSM 6 (which we found more stable for line-based text)
text = pytesseract.image_to_string(page_corrected, config='--psm 6')

print("="*60)
print("PAGE 2 OCR TEXT (Snippet around JSW)")
print("="*60)

# Filter lines containing JSW
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'JSW' in line.upper():
        print(f"Line {i}: {line}")
        # Print a few lines around it
        for j in range(max(0, i-2), min(len(lines), i+3)):
            if j != i:
                print(f"  Line {j}: {lines[j]}")

print("="*60)
