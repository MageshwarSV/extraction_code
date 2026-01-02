# batch_ewb_test.py - Test EWB extraction on all PDFs in test folder
import sys
import os
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.odsfhiaclient1_format11_format1 import run

test_folder = r'c:\Users\avin4\Desktop\boostentryai ui code\test'
output_file = os.path.join(test_folder, 'ewb_extraction_results.txt')

# Get all PDFs
# pdfs = [f for f in os.listdir(test_folder) if f.lower().endswith('.pdf')]
pdfs = ['test1.pdf']
print(f"Found {len(pdfs)} PDFs to process")

results = []
results.append(f"EWB Extraction Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
results.append("=" * 80)
results.append("")

for i, pdf_name in enumerate(pdfs, 1):
    pdf_path = os.path.join(test_folder, pdf_name)
    print(f"[{i}/{len(pdfs)}] Processing: {pdf_name}...")
    
    start_time = datetime.now()
    try:
        r = run(pdf_path)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        ewb_no = r.get('E-Way Bill No') or 'NOT FOUND'
        total_fields = sum(1 for v in r.values() if v is not None)
        
        result_line = f"{pdf_name}"
        result_line += f"\n  Path: {pdf_path}"
        result_line += f"\n  EWB No: {ewb_no}"
        result_line += f"\n  Fields: {total_fields}/22"
        result_line += f"\n  Time: {duration:.2f}s"
        result_line += "\n"
        
        results.append(result_line)
        print(f"  EWB No: {ewb_no} | Fields: {total_fields}/22 | Time: {duration:.2f}s")
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result_line = f"{pdf_name}"
        result_line += f"\n  Path: {pdf_path}"
        result_line += f"\n  ERROR: {str(e)}"
        result_line += f"\n  Time: {duration:.2f}s"
        result_line += "\n"
        
        results.append(result_line)
        print(f"  ERROR: {str(e)} | Time: {duration:.2f}s")

# Summary
results.append("")
results.append("=" * 80)
results.append(f"Total PDFs: {len(pdfs)}")
ewb_found = sum(1 for r in results if 'EWB No: ' in r and 'NOT FOUND' not in r)
results.append(f"EWB Found: {ewb_found}")
results.append(f"EWB Not Found: {len(pdfs) - ewb_found}")

# Save to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f"\nResults saved to: {output_file}")
