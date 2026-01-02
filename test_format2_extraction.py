"""
Test the Format 2 extractor with the uploaded invoice image
"""

import sys
import json
sys.path.insert(0, r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.client1_format2 import run

# Test with uploaded Format 2 invoice
# First convert the JPG to a PDF for testing
from PIL import Image

image_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/uploaded_image_1766467732793.jpg"
pdf_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/test_format2_invoice.pdf"

# Convert image to PDF
img = Image.open(image_path)
img_rgb = img.convert('RGB')
img_rgb.save(pdf_path, 'PDF')
print(f"✓ Converted image to PDF: {pdf_path}")

# Run extraction
print("\n" + "=" * 80)
print("TESTING FORMAT 2 EXTRACTOR")
print("=" * 80)

result = run(pdf_path)

print("\n" + "=" * 80)
print("EXTRACTION RESULTS")
print("=" * 80)
print(json.dumps(result, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
fields_extracted = sum(1 for v in result.values() if v is not None and v != "")
total_fields = len(result)
print(f"Fields extracted: {fields_extracted}/{total_fields}")
print(f"Success rate: {fields_extracted/total_fields*100:.1f}%")

# Show key fields
print("\nKey Fields:")
key_fields = ["Invoice No", "Invoice Date", "Consignee", "Vehicle", "E-Way Bill No", "L.R. No"]
for field in key_fields:
    value = result.get(field, "NOT IN RESULT")
    print(f"  {field}: {value}")
