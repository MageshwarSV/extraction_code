# Extract GC numbers and save to txt file with page numbers
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
from engine.extractors.gc_number_extractor import extract_page_type_and_gc

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"
output_file = f"{save_dir}\\extracted_gc_numbers.txt"

print("Extracting GC numbers...")
pages = convert_from_path(pdf_path, dpi=300)

results = []
for i, page in enumerate(pages, 1):
    page_type, gc_num = extract_page_type_and_gc(page)
    if page_type == "CONSIGNMENT":
        results.append((i, gc_num or "-"))
        print(f"Page {i}: {gc_num or '-'}")

# Save to txt file
with open(output_file, 'w') as f:
    f.write("GC NUMBER EXTRACTION RESULTS\n")
    f.write("=" * 40 + "\n\n")
    f.write(f"{'Page':<10} {'GC Number':<15}\n")
    f.write("-" * 25 + "\n")
    
    for page_num, gc_num in results:
        f.write(f"{page_num:<10} {gc_num:<15}\n")
    
    f.write("\n" + "-" * 25 + "\n")
    f.write(f"Total: {len(results)} consignment pages\n")
    found = sum(1 for _, gc in results if gc != "-")
    f.write(f"Extracted: {found}/{len(results)} ({100*found/len(results):.0f}%)\n")

print(f"\nSaved to: {output_file}")
