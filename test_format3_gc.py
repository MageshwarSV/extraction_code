# Quick test of client1_format3.py with GC extraction
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.client1_format3 import extract_format3_data

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\format3_results.txt"

result = extract_format3_data(pdf_path)

with open(save_path, 'w') as f:
    f.write("FORMAT 3 EXTRACTION RESULTS\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Branch: {result.get('Branch') or 'NOT FOUND'}\n")
    f.write(f"Invoice Date: {result.get('Invoice_Date') or 'NOT FOUND'}\n")
    f.write(f"\nTotal Pages: {result.get('total_pages')}\n")
    f.write(f"Consignment Pages: {result.get('consignment_pages')}\n")
    f.write(f"\nGC NUMBERS ({len(result.get('GC_Numbers', []))}):\n")
    f.write("-" * 30 + "\n")
    for gc in result.get('GC_Numbers', []):
        f.write(f"  Page {gc['page']}: {gc['gc_number']}\n")
    f.write("\n" + "=" * 50 + "\n")
    f.write(f"Status: {result.get('status')}\n")

print(f"Results saved to: {save_path}")
