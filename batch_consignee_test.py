# batch_consignee_test.py - Test Consignee extraction on all PDFs in test folder
import sys
import os
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.client1_format1 import run

test_folder = r'c:\Users\avin4\Desktop\boostentryai ui code\test'
output_file = os.path.join(test_folder, 'consignee_extraction_results.txt')

# Get all PDFs
pdfs = [f for f in os.listdir(test_folder) if f.lower().endswith('.pdf')]
print(f"Found {len(pdfs)} PDFs to process")

results = []
results.append(f"Consignee Extraction Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
results.append("=" * 80)
results.append("")

for i, pdf_name in enumerate(pdfs, 1):
    pdf_path = os.path.join(test_folder, pdf_name)
    print(f"[{i}/{len(pdfs)}] Processing: {pdf_name}...")
    
    try:
        r = run(pdf_path)
        consignee = r.get('Consignee') or 'NOT FOUND'
        
        result_line = f"{pdf_name}"
        result_line += f"\n  Path: {pdf_path}"
        result_line += f"\n  Consignee: {consignee}"
        result_line += "\n"
        
        results.append(result_line)
        print(f"  Consignee: {consignee}")
        
    except Exception as e:
        result_line = f"{pdf_name}"
        result_line += f"\n  Path: {pdf_path}"
        result_line += f"\n  ERROR: {str(e)}"
        result_line += "\n"
        
        results.append(result_line)
        print(f"  ERROR: {str(e)[:50]}")

# Save to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f"\nResults saved to: {output_file}")
