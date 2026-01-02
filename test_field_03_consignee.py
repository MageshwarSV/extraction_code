"""
TEST SCRIPT 3: Extract Consignee (Tube Syndicate)
Test on Format 2 invoice to verify consignee extraction
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
print("TEST 3: CONSIGNEE EXTRACTION (Tube Syndicate)")
print("=" * 80)

# Show relevant lines
print("\nSearching for 'Ship To' or company names in OCR text...")
lines = text.splitlines()
for i, line in enumerate(lines):
    if 'Ship To' in line or 'DSKATSYN' in line or 'Tube' in line or 'Syndicate' in line:
        print(f"  Line {i}: {line}")

print("\n" + "-" * 80)
print("EXTRACTION PATTERNS TESTING")
print("-" * 80)

# Strategy 1: Look for "Ship To:" and extract next lines
print("\n[Strategy 1] Finding 'Ship To:' label...")
for i, line in enumerate(lines):
    if re.search(r'Ship\s*To\s*[:.-]', line, re.IGNORECASE):
        print(f"  Found 'Ship To' at line {i}: {line}")
        # Check next 5 lines
        for j in range(i+1, min(i+6, len(lines))):
            cand = lines[j].strip()
            print(f"    Line {j}: {cand}")
            # Check if this looks like a company name
            if cand and len(cand) > 3 and 'GST' not in cand and 'State' not in cand:
                # Skip DSKATSYN01 code
                if not re.match(r'^[A-Z]{3,}\d+$', cand):
                    print(f"  ✓ Potential consignee: {cand}")

# Strategy 2: Look for pattern after codes
print("\n[Strategy 2] Looking for company name pattern...")
# Pattern: After DSKATSYN01, look for company name
for i, line in enumerate(lines):
    if re.match(r'[A-Z]{3,}\d+', line.strip()):
        print(f"  Found code at line {i}: {line}")
        # Next line might be company
        if i+1 < len(lines):
            next_line = lines[i+1].strip()
            print(f"    Next line: {next_line}")
            if 'Tube' in next_line or 'Syndicate' in next_line:
                print(f"  ✓ Found company: {next_line}")

# Strategy 3: Direct search for "Tube Syndicate"
print("\n[Strategy 3] Direct pattern matching...")
pattern = r'(Tube\s+Syndicate)'
match = re.search(pattern, text, re.IGNORECASE)
if match:
    print(f"  ✓ Direct match: {match.group(1)}")

print("\n" + "=" * 80)
print("EXPECTED: Tube Syndicate")
print("=" * 80)
