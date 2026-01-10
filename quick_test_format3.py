# Quick test to show client1_format3 results
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.client2_format2 import extract_format3_data

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Running client1_format3 extraction...")
result = extract_format3_data(pdf_path)

print("\nRESULTS:")
print(f"  Branch: {result.get('Branch')}")
print(f"  Invoice_Date: {result.get('Invoice_Date')}")
print(f"  Status: {result.get('status')}")
print(f"  Total Pages: {result.get('total_pages')}")
