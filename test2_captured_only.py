# test2_captured_only.py
"""
TEST 2: Run optimized captured image extraction only
"""
import sys, time
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

print("="*70)
print("TEST 2: OPTIMIZED CAPTURED IMAGE")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print("="*70)

from engine.extractors.client1_format1 import run

captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

start = time.time()
result = run(captured)
elapsed = time.time() - start

print(f"\nCompleted: {datetime.now().strftime('%H:%M:%S')}")
print(f"TIME: {elapsed:.1f}s ({elapsed/60:.1f}min)")
print(f"Invoice: {result.get('Invoice No', 'NOT FOUND')}")
print(f"Vehicle: {result.get('Vehicle', 'NOT FOUND')}")

if elapsed > 90:
    print(f"\nWARNING: Exceeds 90s by {elapsed-90:.1f}s")
else:
    print(f"\nSUCCESS: Under 90s target!")
    
print("="*70)
