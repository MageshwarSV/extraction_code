#!/usr/bin/env python3
"""
Test client1.py (no optimization) with uploaded image
"""

import sys
import time
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

uploaded_img = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766388702771.jpg'

print("Testing client1.py (full accuracy, no optimization)...")

# Create PDF
img = Image.open(uploaded_img)
pdf_path = 'test_full_accuracy.pdf'
img_width, img_height = img.size
page_width = 595
page_height = int(page_width * img_height / img_width)

c = canvas.Canvas(pdf_path, pagesize=(page_width, page_height))
c.drawImage(ImageReader(img), 0, 0, width=page_width, height=page_height)
c.save()

print(f"Created: {pdf_path}")

# Extract using client1.py (full accuracy)
from engine.extractors import client1

start = time.time()
result = client1.run(pdf_path)
extract_time = time.time() - start

print(f"\nExtraction completed in {extract_time:.2f}s ({extract_time/60:.1f} min)")

# Save to TXT
output_file = 'client1_output.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("CLIENT1.PY EXTRACTION (FULL ACCURACY)\n")
    f.write("="*80 + "\n\n")
    f.write(f"Extraction Time: {extract_time:.2f}s ({extract_time/60:.1f} min)\n\n")
    f.write("EXTRACTED FIELDS:\n")
    f.write("-"*80 + "\n\n")
    
    if result:
        for key, val in result.items():
            if key not in ['raw_ocr_text', 'final_text']:
                f.write(f"{key}: {val}\n")
    else:
        f.write("No results returned\n")

print(f"\nSaved to: {output_file}")
print(f"\nFull path: c:\\Users\\avin4\\Desktop\\wbai_doc_extractor_engine-maincopy\\{output_file}")

# Show preview
if result:
    print("\nExtracted Data Preview:")
    print(f"  Consignee: {result.get('Consignee', 'N/A')}")
    print(f"  Invoice No: {result.get('Invoice No', 'N/A')}")
    print(f"  Date: {result.get('Date', 'N/A')}")
    print(f"  Vehicle: {result.get('Vehicle', 'N/A')}")
