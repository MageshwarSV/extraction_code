"""
TEST SCRIPT 5: Extract Total Quantity (from TOTAL row)
Test on Format 2 invoice to verify quantity extraction from table
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
print("TEST 5: TOTAL QUANTITY EXTRACTION (from TOTAL row)")
print("=" * 80)

# Show relevant lines
print("\nSearching for 'TOTAL' in OCR text...")
lines = text.splitlines()
for i, line in enumerate(lines):
    if 'TOTAL' in line.upper():
        print(f"  Line {i}: {line}")
        # Show next 2 lines too
        if i+1 < len(lines):
            print(f"  Line {i+1}: {lines[i+1]}")
        if i+2 < len(lines):
            print(f"  Line {i+2}: {lines[i+2]}")

print("\n" + "-" * 80)
print("EXTRACTION PATTERNS TESTING")
print("-" * 80)

# Test Pattern 1: TOTAL followed by number with 3 decimals
pattern1 = r'TOTAL.*?(\d+\.\d{3})'
match1 = re.search(pattern1, text, re.IGNORECASE)
if match1:
    print(f"✓ Pattern 1 SUCCESS: {match1.group(1)} MT")
else:
    print("✗ Pattern 1 FAILED")

# Test Pattern 2: TOTAL in line, number with 2-3 decimals
pattern2 = r'TOTAL\s+(\d+\.\d{2,3})'
match2 = re.search(pattern2, text, re.IGNORECASE)
if match2:
    print(f"✓ Pattern 2 SUCCESS: {match2.group(1)} MT")
else:
    print("✗ Pattern 2 FAILED")

# Test Pattern 3: Look at lines containing TOTAL
print("\n[Strategy 3] Line-by-line search...")
for i, line in enumerate(lines):
    if 'TOTAL' in line.upper():
        # Look for decimal numbers in this line and next 2 lines
        search_text = ' '.join(lines[i:min(i+3, len(lines))])
        nums = re.findall(r'(\d+\.\d{3})', search_text)
        if nums:
            print(f"  ✓ Found quantities near TOTAL: {nums}")
            print(f"    Likely total: {nums[0]} MT")

print("\n" + "=" * 80)
print("EXPECTED: 15.419 MT")
print("=" * 80)
