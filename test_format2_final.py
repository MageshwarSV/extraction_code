"""
Test Format 2 extractor with the uploaded Jindal Format 2 invoice
"""

import sys
import json
sys.path.insert(0, r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.client1_format2 import run
from PIL import Image

# Convert uploaded image to PDF
image_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/uploaded_image_1766468893270.jpg"
pdf_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/test_format2_jindal.pdf"

# Convert image to PDF
print("Converting image to PDF...")
img = Image.open(image_path)
img_rgb = img.convert('RGB')
img_rgb.save(pdf_path, 'PDF')
print(f"✓ Created PDF: {pdf_path}\n")

# Run Format 2 extraction
print("=" * 80)
print("TESTING FORMAT 2 EXTRACTOR")
print("=" * 80)

result = run(pdf_path)

print("\n" + "=" * 80)
print("EXTRACTION RESULTS")
print("=" * 80)
print(json.dumps(result, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("FIELD EXTRACTION SUMMARY")
print("=" * 80)
fields_extracted = sum(1 for v in result.values() if v is not None and v != "")
total_fields = len(result)
print(f"Success: {fields_extracted}/{total_fields} fields extracted ({fields_extracted/total_fields*100:.1f}%)")

print("\n" + "=" * 80)
print("KEY FIELDS CHECK")
print("=" * 80)
key_fields = [
    "Invoice No",
    "Invoice Date", 
    "E-Way Bill No",
    "Consignee",
    "Vehicle",
    "Actual Weight",
    "Rate",
]
for field in key_fields:
    value = result.get(field, "NOT FOUND")
    status = "✓" if value and value != "NOT FOUND" else "✗"
    print(f"{status} {field}: {value}")
