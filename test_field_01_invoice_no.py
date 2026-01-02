"""
TEST SCRIPT 1: Extract Invoice Number
Test on Format 2 invoice to verify Invoice No extraction
"""

import sys
sys.path.insert(0, r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from PIL import Image
import pytesseract
import re

# Load the invoice image
image_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/uploaded_image_1766469357550.jpg"
img = Image.open(image_path)

# Run OCR
text = pytesseract.image_to_string(img, lang='eng')

print("=" * 80)
print("TEST 1: INVOICE NUMBER EXTRACTION")
print("=" * 80)

# Show relevant lines
print("\nSearching for 'Invoice No' in OCR text...")
for line in text.splitlines():
    if 'Invoice' in line and 'No' in line:
        print(f"  Found line: {line}")

print("\n" + "-" * 80)
print("EXTRACTION PATTERNS TESTING")
print("-" * 80)

# Test Pattern 1: Invoice No : CN25000862
pattern1 = r'Invoice\s*No\s*[:.-]\s*([A-Z]{2}\d{7,10})'
match1 = re.search(pattern1, text, re.IGNORECASE)
if match1:
    print(f"✓ Pattern 1 SUCCESS: {match1.group(1)}")
else:
    print("✗ Pattern 1 FAILED")

# Test Pattern 2: More flexible
pattern2 = r'Invoice\s*No\s*[:.-]?\s*([A-Z0-9]{8,15})'
match2 = re.search(pattern2, text, re.IGNORECASE)
if match2:
    print(f"✓ Pattern 2 SUCCESS: {match2.group(1)}")
else:
    print("✗ Pattern 2 FAILED")

# Test Pattern 3: Very flexible
pattern3 = r'(?:Invoice|INV).*?No.*?[:.-]?\s*([A-Z]{2}\d{8})'
match3 = re.search(pattern3, text, re.IGNORECASE | re.DOTALL)
if match3:
    print(f"✓ Pattern 3 SUCCESS: {match3.group(1)}")
else:
    print("✗ Pattern 3 FAILED")

print("\n" + "=" * 80)
print("EXPECTED: CN25000862")
print("=" * 80)
