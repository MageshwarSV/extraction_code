# test_ocr_no_textlayer.py
"""
1. Remove text layer from PDF
2. Run extraction using client1_format1.py
3. Measure time
"""
import os
import sys
import time
import fitz  # PyMuPDF

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

source_pdf = r'c:\Users\avin4\Desktop\boostentryai ui code\test\1234yyy.pdf'
output_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_no_textlayer.pdf'

print("=" * 60)
print("TEST: OCR Extraction with Text Layer Removed")
print("=" * 60)

# Step 1: Remove text layer from PDF
print("\nStep 1: Removing text layer from PDF...")
doc = fitz.open(source_pdf)
new_doc = fitz.open()

for page_num, page in enumerate(doc):
    # Render page to image
    pix = page.get_pixmap(dpi=150)
    
    # Create new page with just the image (no text layer)
    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
    
    # Insert the image
    img_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
    new_page.insert_image(img_rect, pixmap=pix)

new_doc.save(output_pdf)
new_doc.close()
doc.close()

# Verify text layer is removed
doc = fitz.open(output_pdf)
text_len = len(doc[0].get_text().strip())
doc.close()
print(f"Created: {output_pdf}")
print(f"Text layer chars: {text_len} (should be 0 or minimal)")

# Step 2: Run extraction
print("\nStep 2: Running extraction (OCR path)...")
from engine.extractors.client1_format1 import run

start_time = time.time()
result = run(output_pdf)
elapsed = time.time() - start_time

print(f"\nExtraction completed in {elapsed:.2f} seconds")

# Show key fields
print("\n--- Extracted Fields ---")
for key in ['Consignee', 'Invoice No', 'Invoice Date', 'E-Way Bill No', 'Vehicle']:
    val = result.get(key, 'NOT FOUND')
    print(f"  {key}: {val}")

print("=" * 60)
