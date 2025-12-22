#!/usr/bin/env python3
"""
Run client1.py on the specified PDF
"""

import sys
import time
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors import client1

pdf_path = r'c:\Users\avin4\Desktop\boostentryai ui code\1234567890120.pdf'

print("="*80)
print("RUNNING client1.py EXTRACTION")
print("="*80)
print(f"\nPDF: {pdf_path}\n")

start = time.time()
result = client1.run(pdf_path)
extract_time = time.time() - start

print(f"\n{'='*80}")
print(f"EXTRACTION COMPLETED IN {extract_time:.2f}s ({extract_time/60:.1f} min)")
print("="*80)

# Save to TXT
output_file = 'client1_extraction_result.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("CLIENT1.PY EXTRACTION RESULTS\n")
    f.write("="*80 + "\n\n")
    f.write(f"PDF: {pdf_path}\n")
    f.write(f"Extraction Time: {extract_time:.2f}s ({extract_time/60:.1f} min)\n\n")
    f.write("EXTRACTED FIELDS:\n")
    f.write("-"*80 + "\n\n")
    
    if result:
        for key, val in result.items():
            if key not in ['raw_ocr_text', 'final_text']:
                f.write(f"{key}: {val}\n")
    else:
        f.write("No results returned\n")

print(f"\n✓ Saved to: {output_file}")
print(f"Full path: c:\\Users\\avin4\\Desktop\\wbai_doc_extractor_engine-maincopy\\{output_file}")

# Print results
if result:
    print("\n" + "="*80)
    print("EXTRACTED DATA:")
    print("="*80)
    for key, val in result.items():
        if key not in ['raw_ocr_text', 'final_text']:
            print(f"{key}: {val}")
