"""
Test Invoice Date Extractor with Actual Format 3 Document
User will verify if extraction is correct
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

# Load actual OCR text from Format 3 document
with open(r'c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_ocr_text.txt', 'r', encoding='utf-8') as f:
    actual_text = f.read()

print("=" * 80)
print("INVOICE DATE EXTRACTION - FORMAT 3 ACTUAL DOCUMENT")
print("=" * 80)

print("\nSearching for 'Invoice Date/Time' in document...")
print("-" * 80)

# Show relevant lines
for i, line in enumerate(actual_text.split('\n'), 1):
    if 'INVOICE' in line.upper() or 'DATE' in line.upper():
        if any(char.isdigit() and '.' in line for char in line):
            print(f"Line {i}: {line}")

print("\n" + "=" * 80)
print("EXTRACTION RESULT")
print("=" * 80)

result = extract_invoice_date_format3(actual_text)

if result:
    print(f"\n✅ Successfully Extracted Invoice Date: {result}")
    print(f"\n   Format: DD.MM.YYYY")
    print(f"   Extracted: {result}")
else:
    print("\n❌ Failed to extract Invoice Date")

print("\n" + "=" * 80)
print("👉 USER: Please verify if this date is correct!")
print("=" * 80)
