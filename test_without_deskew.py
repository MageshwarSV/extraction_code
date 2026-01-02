"""
Format 3 Complete Extraction - WITHOUT DESKEW (for debugging)
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
from engine.extractors.gc_number_extractor import extract_gc_number_from_pdf_page
import logging

logging.basicConfig(level=logging.WARNING)

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Testing extraction WITHOUT deskew preprocessing...")
print("=" * 60)

# Test page 2 (known invoice page)
pages = convert_from_path(pdf_path, dpi=200, first_page=2, last_page=2)
page = pages[0]

print(f"\nPage 2 - Testing direct OCR:")
print(f"  Image size: {page.size}")

# Direct OCR - NO preprocessing
text = pytesseract.image_to_string(page, config='--psm 6')

print(f"  OCR text length: {len(text)} characters")
print(f"  First 300 chars: {repr(text[:300])}")

# Extract
branch = extract_branch_refined(text)
date = extract_invoice_date_format3(text)

print(f"\nExtraction Results:")
print(f"  Branch: {branch}")
print(f"  Date: {date}")
print(f"\nExpected: Branch=POTTANERI, Date=12.12.2025")
print("=" * 60)
