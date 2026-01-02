"""
TEST SCRIPT 2: Extract Invoice Date (Dated field)
Test on Format 2 invoice to verify date extraction
"""

import sys
sys.path.insert(0, r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from PIL import Image
import pytesseract
import re
from datetime import datetime

# Load the invoice image
image_path = r"C:/Users/avin4/.gemini/antigravity/brain/cec27e78-f50d-497c-a7b1-e2cdbd677d79/uploaded_image_1766469357550.jpg"
img = Image.open(image_path)

# Run OCR
text = pytesseract.image_to_string(img, lang='eng')

print("=" * 80)
print("TEST 2: INVOICE DATE EXTRACTION (Dated field)")
print("=" * 80)

# Show relevant lines
print("\nSearching for 'Dated' in OCR text...")
for line in text.splitlines():
    if 'Dated' in line or 'Date' in line:
        print(f"  Found line: {line}")

print("\n" + "-" * 80)
print("EXTRACTION PATTERNS TESTING")
print("-" * 80)

# Test Pattern 1: Dated: 07.11.2025
pattern1 = r'Dated\s*[:.-]\s*(\d{2}\.\d{2}\.\d{4})'
match1 = re.search(pattern1, text, re.IGNORECASE)
if match1:
    print(f"✓ Pattern 1 SUCCESS: {match1.group(1)}")
else:
    print("✗ Pattern 1 FAILED")

# Test Pattern 2: Dated: 07-11-2025 or 07/11/2025
pattern2 = r'Dated\s*[:.-]\s*(\d{2}[./-]\d{2}[./-]\d{4})'
match2 = re.search(pattern2, text, re.IGNORECASE)
if match2:
    date_str = match2.group(1)
    # Try to parse
    for fmt in ["%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"]:
        try:
            parsed = datetime.strptime(date_str, fmt)
            print(f"✓ Pattern 2 SUCCESS: {date_str} → {parsed.strftime('%d.%m.%Y')}")
            break
        except:
            continue
else:
    print("✗ Pattern 2 FAILED")

# Test Pattern 3: More flexible
pattern3 = r'Dated[:.\s-]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})'
match3 = re.search(pattern3, text, re.IGNORECASE)
if match3:
    print(f"✓ Pattern 3 SUCCESS: {match3.group(1)}")
else:
    print("✗ Pattern 3 FAILED")

print("\n" + "=" * 80)
print("EXPECTED: 07.11.2025")
print("=" * 80)
