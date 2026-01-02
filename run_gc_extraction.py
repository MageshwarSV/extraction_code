# Run GC extraction and save results to file
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
from engine.extractors.gc_number_extractor import extract_page_type_and_gc

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\gc_results.txt"

print("Running GC extraction...")
pages = convert_from_path(pdf_path, dpi=200)

results = []
for i, page in enumerate(pages, 1):
    page_type, gc_num = extract_page_type_and_gc(page)
    results.append((i, page_type, gc_num))
    print(f"Page {i}: {page_type} - {gc_num or '-'}")

# Save to file
with open(output_path, 'w') as f:
    f.write("GC NUMBER EXTRACTION RESULTS\n")
    f.write("=" * 50 + "\n\n")
    
    consignment_count = 0
    gc_found_count = 0
    
    for page_num, page_type, gc_num in results:
        if page_type == "CONSIGNMENT":
            consignment_count += 1
            if gc_num:
                gc_found_count += 1
            f.write(f"Page {page_num:2}: {gc_num or '-':>10}\n")
    
    f.write("\n" + "=" * 50 + "\n")
    f.write(f"Consignment Pages: {consignment_count}\n")
    f.write(f"GC Numbers Found: {gc_found_count}/{consignment_count}\n")
    f.write(f"Success Rate: {100*gc_found_count/max(consignment_count,1):.0f}%\n")

print(f"\nResults saved to: {output_path}")
