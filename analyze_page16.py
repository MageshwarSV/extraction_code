"""
Analyze Page 16 - The Missing 11th Invoice
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.deskew import deskew_and_enhance
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("=" * 80)
print("ANALYZING PAGE 16 - MISSING INVOICE")
print("=" * 80)

# Extract page 16
print("\n📄 Extracting page 16...")
pages = convert_from_path(pdf_path, dpi=300, first_page=16, last_page=16)
page16 = pages[0]

# Apply deskew
print("🔧 Applying deskew...")
page16_corrected = deskew_and_enhance(page16)

# OCR
print("🔍 Running OCR...")
text = pytesseract.image_to_string(page16_corrected, lang='eng', config='--psm 6')

# Check for invoice markers
print(f"\nContains 'INVOICE': {'INVOICE' in text.upper()}")
print(f"Contains 'DATE': {'DATE' in text.upper()}")

# Extract data
branch = extract_branch_refined(text)
date = extract_invoice_date_format3(text)

print("\n" + "=" * 80)
print("EXTRACTION RESULTS:")
print("=" * 80)
print(f"Branch: {branch or 'NOT FOUND'}")
print(f"Date: {date or 'NOT FOUND'}")

# Show relevant lines
print("\n" + "=" * 80)
print("RELEVANT TEXT LINES:")
print("=" * 80)
for i, line in enumerate(text.split('\n'), 1):
    if any(word in line.upper() for word in ['POST', 'BILA', 'DATE', 'INVOICE', 'TAX']):
        print(f"{i:3d}: {line}")

print("\n" + "=" * 80)
print("👉 Expected: Branch = BILAKALAGUDUR")
print(f"👉 Got: Branch = {branch or 'NOT FOUND'}")
print("=" * 80)
