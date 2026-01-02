# Debug Page 15 date extraction
import sys
import os
sys.path.insert(0, os.getcwd())

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

# Convert page 15
pages = convert_from_path(pdf_path, dpi=300, first_page=15, last_page=15)
page = pages[0]

# Deskew (same as main script)
from engine.extractors.deskew import deskew_and_enhance
page_corrected = deskew_and_enhance(page)

# Get full OCR text with PSM 3 (the current setting)
text_psm3 = pytesseract.image_to_string(page_corrected, config='--psm 3')
text_psm6 = pytesseract.image_to_string(page_corrected, config='--psm 6')

print("=" * 70)
print("PAGE 15 DATE DEBUG")
print("=" * 70)

print("\n--- PSM 3 TEXT (Lines with Date) ---")
for line in text_psm3.split('\n'):
    if 'date' in line.lower():
        print(f"  {line}")

print("\n--- PSM 6 TEXT (Lines with Date) ---")
for line in text_psm6.split('\n'):
    if 'date' in line.lower():
        print(f"  {line}")

# Try the actual extractor
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
date_psm3 = extract_invoice_date_format3(text_psm3)
date_psm6 = extract_invoice_date_format3(text_psm6)

print(f"\nExtracted (PSM 3): {date_psm3}")
print(f"Extracted (PSM 6): {date_psm6}")
