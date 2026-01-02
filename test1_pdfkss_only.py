# test1_pdfkss_only.py
"""
TEST 1: Run PDFKSS extraction only
"""
import sys, time
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

print("="*70)
print("TEST 1: PDFKSS ONLY")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print("="*70)

from engine.extractors.odsfhiaclient1_format11_format1 import run

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'

start = time.time()
result = run(pdfkss)
elapsed = time.time() - start

print(f"\nCompleted: {datetime.now().strftime('%H:%M:%S')}")
print(f"TIME: {elapsed:.1f}s ({elapsed/60:.1f}min)")
print(f"Invoice: {result.get('Invoice No', 'NOT FOUND')}")
print(f"Vehicle: {result.get('Vehicle', 'NOT FOUND')}")
print("="*70)
