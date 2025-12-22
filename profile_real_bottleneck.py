#!/usr/bin/env python3
"""
REAL PROFILING - Where is the actual time spent?

Theory: Preprocessing won't help if the bottleneck is elsewhere
"""

import sys
import time
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.client1_format1 import run

# Test with uploaded camera image
pdf_path = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\camera_preprocessed.pdf'

print("="*80)
print("DETAILED PROFILING - Find the REAL bottleneck")
print("="*80)

# Add detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

print("\nRunning extraction with FULL logging...")
print("This will show us WHERE the time is actually spent\n")

start = time.time()
result = run(pdf_path)
total_time = time.time() - start

print("\n" + "="*80)
print(f"TOTAL TIME: {total_time:.2f}s")
print("="*80)

print("\nCheck the logs above to see:")
print("1. Tesseract OCR timing")
print("2. PDF rendering timing")
print("3. Delivery address timing")
print("4. Field extraction timing")
print("\nThe biggest number is the real bottleneck!")
