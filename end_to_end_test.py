#!/usr/bin/env python3
"""
COMPLETE END-TO-END TEST
1. Upload image → PDF (like upload_routes.py)
2. Extract data (client1_format1.py)
3. Save results to TXT
"""

import sys
import time
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import json

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

# Input image
uploaded_img = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766384142541.jpg'

print("="*80)
print("END-TO-END EXTRACTION TEST")
print("="*80)

# STEP 1: Convert image to PDF (like upload_routes.py)
print("\n[STEP 1] Converting image to PDF (upload_routes.py simulation)...")
start = time.time()

img = Image.open(uploaded_img)
print(f"  Image size: {img.size}")

# Create PDF
pdf_path = 'uploaded_invoice.pdf'
img_width, img_height = img.size

# A4-like aspect ratio
page_width = 595  # A4 width in points
page_height = int(page_width * img_height / img_width)

c = canvas.Canvas(pdf_path, pagesize=(page_width, page_height))
c.drawImage(ImageReader(img), 0, 0, width=page_width, height=page_height)
c.save()

step1_time = time.time() - start
print(f"  Created: {pdf_path}")
print(f"  Time: {step1_time:.2f}s")

# STEP 2: Extract data (client1_format1.py)
print("\n[STEP 2] Running extraction (client1_format1.py)...")
from engine.extractors.client1_format1 import run

start = time.time()
result = run(pdf_path)
step2_time = time.time() - start

print(f"  Extraction completed!")
print(f"  Time: {step2_time:.2f}s")

# STEP 3: Save to TXT
print("\n[STEP 3] Saving results to TXT...")
output_txt = 'extraction_output.txt'

with open(output_txt, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("EXTRACTION RESULTS\n")
    f.write("="*80 + "\n\n")
    
    f.write(f"Input Image: {uploaded_img}\n")
    f.write(f"PDF Created: {pdf_path}\n")
    f.write(f"Extraction Time: {step2_time:.2f}s\n\n")
    
    f.write("-"*80 + "\n")
    f.write("EXTRACTED FIELDS\n")
    f.write("-"*80 + "\n\n")
    
    # Write all fields
    if isinstance(result, dict):
        for key, value in result.items():
            if key not in ['raw_ocr_text', 'final_text', 'timing']:
                f.write(f"{key}: {value}\n")
        
        # Add timing info if available
        if 'timing' in result:
            f.write("\n" + "-"*80 + "\n")
            f.write("TIMING BREAKDOWN\n")
            f.write("-"*80 + "\n\n")
            for k, v in result['timing'].items():
                f.write(f"{k}: {v}\n")
        
        # Add raw OCR text at the end
        if 'final_text' in result:
            f.write("\n" + "="*80 + "\n")
            f.write("FULL OCR TEXT\n")
            f.write("="*80 + "\n\n")
            f.write(result['final_text'])
    else:
        f.write("Result format unexpected:\n")
        f.write(str(result))


print(f"  Saved: {output_txt}")

# Print summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal Time: {step1_time + step2_time:.2f}s")
print(f"  - PDF Creation: {step1_time:.2f}s")
print(f"  - Extraction:   {step2_time:.2f}s")

print(f"\n✅ OUTPUT FILE:")
print(f"   {output_txt}")

print(f"\nExtracted Data Preview:")
print(f"  Invoice No: {result.get('Invoice No', 'N/A')}")
print(f"  Date: {result.get('Date', 'N/A')}")
print(f"  Consignee: {result.get('Consignee', 'N/A')}")
print(f"  Amount: {result.get('Amount', 'N/A')}")

print("\n" + "="*80)
print(f"Full results saved to: {output_txt}")
print("="*80)
