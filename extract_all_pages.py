# Extract all 20 pages individually
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
from engine.extractors.deskew import deskew_and_enhance

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("=" * 70)
print("FORMAT 3 - ALL 20 PAGES EXTRACTION")
print("=" * 70)

# Convert all pages
print("Converting PDF...")
pages = convert_from_path(pdf_path, dpi=200)
print(f"Total pages: {len(pages)}\n")

print(f"{'Page':<6} {'Branch':<20} {'Invoice Date':<15} {'Type':<10}")
print("-" * 70)

invoice_count = 0
for i, page in enumerate(pages, 1):
    # Preprocess
    try:
        page_prep = deskew_and_enhance(page)
    except:
        page_prep = page
    
    # OCR
    text = pytesseract.image_to_string(page_prep, config='--psm 6')
    
    # Extract
    branch = extract_branch_refined(text)
    date = extract_invoice_date_format3(text)
    
    # Determine type
    if branch or date:
        page_type = "INVOICE"
        invoice_count += 1
    else:
        page_type = "OTHER"
    
    # Display
    branch_str = branch or "-"
    date_str = date or "-"
    print(f"{i:<6} {branch_str:<20} {date_str:<15} {page_type:<10}")

print("-" * 70)
print(f"Total Invoice Pages: {invoice_count}/20")
print("=" * 70)
