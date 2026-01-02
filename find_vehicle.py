# Analyze invoice pages to find Vehicle No pattern
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\vehicle_analysis.txt"

# Invoice pages
invoice_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20]

results = []

print("=" * 70)
print("VEHICLE NUMBER EXTRACTION ANALYSIS")
print("=" * 70 + "\n")

for page_num in invoice_pages:
    print(f"\n--- Page {page_num} ---")
    
    pages = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
    page = pages[0]
    
    text = pytesseract.image_to_string(page, config='--psm 6', lang='eng')
    
    # Find lines containing "Vehicle"
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'vehicle' in line.lower() or 'veh' in line.lower():
            print(f"  Line {i}: {line}")
            
            # Try to extract vehicle number pattern
            # Indian format: XX NN XX NNNN (e.g., TN28BK1910)
            match = re.search(r'([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})', line, re.IGNORECASE)
            if match:
                vehicle = match.group(1).replace(' ', '')
                print(f"    -> Extracted: {vehicle}")
                results.append({"page": page_num, "vehicle": vehicle, "line": line.strip()})

# Save results
with open(output_file, 'w') as f:
    f.write("=" * 70 + "\n")
    f.write("VEHICLE NUMBER EXTRACTION ANALYSIS\n")
    f.write("=" * 70 + "\n\n")
    
    for r in results:
        f.write(f"Page {r['page']:2d}: {r['vehicle']}\n")
        f.write(f"  Line: {r['line'][:80]}\n\n")
    
    f.write("\n" + "=" * 70 + "\n")
    f.write(f"Total vehicles found: {len(results)}\n")

print(f"\n\nResults saved to: {output_file}")
print(f"Total vehicles found: {len(results)}")
