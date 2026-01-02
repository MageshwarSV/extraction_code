# Debug Page 11 vehicle extraction
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

# Convert page 11
pages = convert_from_path(pdf_path, dpi=200, first_page=11, last_page=11)
page = pages[0]

# Get full OCR text
text = pytesseract.image_to_string(page, config='--psm 6', lang='eng')

print("=" * 70)
print("PAGE 11 VEHICLE DEBUG")
print("=" * 70)

# Find lines with Vehicle
print("\n\nSearching for 'Vehicle No' patterns...")
patterns = [
    r'Vehicle\s*No\.?\s*[:\-]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})',
    r'Vehicle\s*(?:No|Number)\.?\s*[:\-/]?\s*([A-Z]{2}\s*[0-9]{1,2}\s*[A-Z]{1,3}\s*[0-9]{3,4})',
    r'Vehicle\s*No\.?\s*[:\-]?\s*([A-Z0-9]{2}\s*[0-9]{1,2}\s*[A-Z0-9]{1,3}\s*[0-9]{3,4})',
    r'Vehicle\s*No\.?\s*([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4})\s+(?:LR|L\s*R)',
    r'Vehicle\s*No\.?\s*[/"\'\-:=\s]*([A-Za-z]{2}\s*[0-9]{1,2}\s*[A-Za-z]{1,3}\s*[0-9]{3,4})',
    r'Vehicle\s*No\b[^A-Za-z0-9]*([A-Za-z]{2}[0-9]{1,2}[A-Za-z0-9]{1,4}[0-9]{2,4})',
    r'Vehicle\s*No\b[^A-Za-z0-9]*([A-Za-z0-9]{8,12})',
]

for i, pattern in enumerate(patterns):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        print(f"Pattern {i+1} matched: '{match.group(1)}'")
        print(f"  Full match: '{match.group(0)}'")

# Also look for the exact "Vehicle No" line
print("\n\nLines containing 'vehicle':")
for line in text.split('\n'):
    if 'vehicle' in line.lower():
        print(f"  {line}")

# Show any AP39 or similar patterns
print("\n\nSearching for 'AP39' pattern anywhere:")
matches = re.findall(r'AP39[A-Z0-9]*', text, re.IGNORECASE)
for m in matches:
    print(f"  Found: {m}")
