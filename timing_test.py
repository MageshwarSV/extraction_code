# timing_test.py
import os, sys, time
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

test_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_no_textlayer.pdf'

print("=" * 60)
print(f"START TIME: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 60)

if os.path.exists(test_pdf):
    print(f"PDF: {test_pdf}")
    print(f"Size: {os.path.getsize(test_pdf)//1024} KB")
    
    from engine.extractors.client1_format1 import run
    
    start = time.time()
    result = run(test_pdf)
    elapsed = time.time() - start
    
    print("=" * 60)
    print(f"END TIME: {datetime.now().strftime('%H:%M:%S')}")
    print(f"TOTAL TIME: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print("=" * 60)
    print(f"Invoice No: {result.get('Invoice No', 'N/A')}")
    print(f"Vehicle: {result.get('Vehicle', 'N/A')}")
else:
    print("Test PDF not found")
