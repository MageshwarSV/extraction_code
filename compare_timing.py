# compare_timing.py
import os, sys, time, fitz
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
from engine.extractors.client1_format1 import run

pdfkss_file = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
test_file = r'c:\Users\avin4\Desktop\boostentryai ui code\test\1234yyy.pdf'

def analyze(path, name):
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    print(f"File: {os.path.basename(path)}")
    print(f"Size: {os.path.getsize(path)//1024} KB")
    
    # Check text layer
    doc = fitz.open(path)
    text_len = len(doc[0].get_text().strip())
    fonts = len(doc[0].get_fonts())
    images = len(doc[0].get_images())
    doc.close()
    
    print(f"Text Layer: {text_len} chars")
    print(f"Fonts: {fonts}, Images: {images}")
    
    # Run extraction with timing
    print(f"\nStart: {datetime.now().strftime('%H:%M:%S')}")
    start = time.time()
    result = run(path)
    elapsed = time.time() - start
    print(f"End: {datetime.now().strftime('%H:%M:%S')}")
    print(f"TIME: {elapsed:.1f} seconds")
    print(f"Invoice: {result.get('Invoice No', 'N/A')}")

# Test pdfkss first
analyze(pdfkss_file, "PDFKSS (Fast)")

# Then test 1234yyy.pdf
analyze(test_file, "TEST (1234yyy.pdf)")
