# simple_test.py
import fitz, time, sys
from datetime import datetime
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

# Test 1: PDFKSS
print("TEST 1: PDFKSS")
print("="*60)
pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'

doc = fitz.open(pdfkss)
text = doc[0].get_text()
print(f"Text layer: {len(text)} chars")
print(f"Has text layer: {'YES' if len(text) > 100 else 'NO'}")
doc.close()

from engine.extractors.client1_format1 import run
print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
start = time.time()
r1 = run(pdfkss)
t1 = time.time() - start
print(f"End: {datetime.now().strftime('%H:%M:%S')}")
print(f"TIME: {t1:.1f}s ({t1/60:.1f}min)")
print(f"Invoice: {r1.get('Invoice No', 'NOT FOUND')}")
print()

# Test 2: Test PDF
print("TEST 2: Test PDF")
print("="*60)
testpdf = r'c:\Users\avin4\Desktop\boostentryai ui code\test\1e2563trufyqdgfwhdk.pdf'

doc = fitz.open(testpdf)
text = doc[0].get_text()
print(f"Text layer: {len(text)} chars")
print(f"Has text layer: {'YES' if len(text) > 100 else 'NO'}")
doc.close()

print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
start = time.time()
r2 = run(testpdf)
t2 = time.time() - start
print(f"End: {datetime.now().strftime('%H:%M:%S')}")
print(f"TIME: {t2:.1f}s ({t2/60:.1f}min)")
print(f"Invoice: {r2.get('Invoice No', 'NOT FOUND')}")
print()

# Comparison
print("COMPARISON")
print("="*60)
print(f"PDFKSS: {t1:.1f}s")
print(f"Test PDF: {t2:.1f}s")
print(f"Difference: {abs(t2-t1):.1f}s")
