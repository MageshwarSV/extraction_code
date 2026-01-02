# -*- coding: utf-8 -*-
from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Converting page 2...")
pages = convert_from_path(pdf_path, dpi=200, first_page=2, last_page=2)
page = pages[0]

print(f"Image: {page.size[0]}x{page.size[1]}, Mode: {page.mode}")

# Try OCR
text = pytesseract.image_to_string(page)
print(f"OCR text length: {len(text)} characters")
print(f"First 200 chars: {repr(text[:200])}")

if len(text) > 10:
    print("SUCCESS - OCR extracted text")
else:
    print("FAILED - No text extracted")
