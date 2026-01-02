# compare_execution_logs.py
"""
Run extraction on both PDFKSS and captured image with detailed logging
Compare what steps execute differently
"""
import sys, time, logging
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

from engine.extractors.odsfhiaclient1_format11_format1 import run

print("="*70)
print("DETAILED EXECUTION COMPARISON")
print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
print("="*70)

# Test 1: PDFKSS
print("\n[TEST 1: PDFKSS]")
print("-"*70)
pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'

start = time.time()
result1 = run(pdfkss)
time1 = time.time() - start

print(f"PDFKSS TIME: {time1:.1f}s")
print(f"Invoice: {result1.get('Invoice No', 'NOT FOUND')}")

# Test 2: Optimized captured image  
print("\n[TEST 2: OPTIMIZED CAPTURED IMAGE]")
print("-"*70)
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

start = time.time()
result2 = run(captured)
time2 = time.time() - start

print(f"CAPTURED TIME: {time2:.1f}s")
print(f"Invoice: {result2.get('Invoice No', 'NOT FOUND')}")

# Comparison
print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"PDFKSS:   {time1:.1f}s")
print(f"Captured: {time2:.1f}s")
print(f"Difference: {abs(time2-time1):.1f}s ({((time2/time1-1)*100):.0f}% {"slower" if time2 > time1 else "faster"})")

if time2 > 90:
    print(f"\n❌ Captured image exceeds 90s target by {time2-90:.1f}s")
else:
    print(f"\n✅ Captured image meets 90s target!")

print("\nCheck logs above to see which steps differ")
print("="*70)
