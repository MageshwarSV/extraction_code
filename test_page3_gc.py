import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
from engine.extractors.gc_number_extractor import extract_gc_number_from_pdf_page
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

print("Testing Page 3 GC Number Extraction")
print("Expected: 14516")
print("=" * 60)

pages = convert_from_path(
    r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf',
    dpi=200,
    first_page=3,
    last_page=3
)

result = extract_gc_number_from_pdf_page(pages[0])

print("=" * 60)
print(f"Result: {result or 'NOT FOUND'}")
print(f"Expected: 14516")
print(f"Match: {'YES' if result == '14516' else 'NO'}")
print("=" * 60)
