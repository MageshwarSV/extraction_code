import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
from pdf2image import convert_from_path
import pytesseract
from engine.extractors.deskew import deskew_and_enhance
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3

pages = convert_from_path(
    r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf', 
    dpi=200, 
    first_page=16, 
    last_page=16
)
page = deskew_and_enhance(pages[0])
text = pytesseract.image_to_string(page, config='--psm 6')

branch = extract_branch_refined(text)
date = extract_invoice_date_format3(text)

print("Page 16 Results:")
print(f"  Branch: {branch}")
print(f"  Date: {date}")
print(f"  Has 'INVOICE': {'INVOICE' in text.upper()}")
print(f"  Has 'DATE': {'DATE' in text.upper()}")
