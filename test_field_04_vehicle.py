"""
TEST SCRIPT 4: Extract Vehicle Number
Test on Format 2 invoice to verify vehicle extraction
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
print("TEST 4: VEHICLE NUMBER EXTRACTION")
print("=" * 80)

# Show relevant lines
print("\nSearching for 'Vehicle' in OCR text...")
for line in text.splitlines():
    if 'Vehicle' in line or 'KA' in line:
        print(f"  Found line: {line}")

print("\n" + "-" * 80)
print("EXTRACTION PATTERNS TESTING")
print("-" * 80)

# Test Pattern 1: Vehicle No:  KA05MS4111
pattern1 = r'Vehicle\s*No\s*[:.-]\s*([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4})'
match1 = re.search(pattern1, text, re.IGNORECASE)
if match1:
    print(f"✓ Pattern 1 SUCCESS: {match1.group(1)}")
else:
    print("✗ Pattern 1 FAILED")

# Test Pattern 2: With spaces in vehicle number
pattern2 = r'Vehicle\s*No\s*[:.-]\s*([A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{3,4})'
match2 = re.search(pattern2, text, re.IGNORECASE)
if match2:
    veh = match2.group(1).replace(' ', '')
    print(f"✓ Pattern 2 SUCCESS: {veh}")
else:
    print("✗ Pattern 2 FAILED")

# Test Pattern 3: Just look for Indian vehicle pattern
pattern3 = r'\b([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})\b'
matches3 = re.findall(pattern3, text)
if matches3:
    print(f"✓ Pattern 3 found {len(matches3)} vehicle-like patterns:")
    for m in matches3:
        print(f"    {m}")
else:
    print("✗ Pattern 3 FAILED")

print("\n" + "=" * 80)
print("EXPECTED: KA05MS4111")
print("=" * 80)
