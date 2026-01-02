import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Testing extraction on page 2 (exactly as before)...")
pages = convert_from_path(pdf_path, dpi=200, first_page=2, last_page=2)
page = pages[0]

# Direct OCR without any preprocessing
text = pytesseract.image_to_string(page, config='--psm 6')

print(f"OCR length: {len(text)}")

# Extract
branch = extract_branch_refined(text)
date = extract_invoice_date_format3(text)

print(f"Branch: {branch}")
print(f"Date: {date}")
print(f"Expected: Branch=POTTANERI, Date=12.12.2025")
