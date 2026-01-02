import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3

print("Debugging extraction failure...")
pages = convert_from_path(
    r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf',
    dpi=200,
    first_page=2,
    last_page=2
)

print(f"Page 2 loaded: {pages[0].size}")

# Direct OCR without preprocessing
text = pytesseract.image_to_string(pages[0], config='--psm 6')
print(f"OCR text length: {len(text)}")
print(f"First 200 chars: {text[:200]}")

# Extract
branch = extract_branch_refined(text)
date = extract_invoice_date_format3(text)

print(f"\nBranch: {branch}")
print(f"Date: {date}")
