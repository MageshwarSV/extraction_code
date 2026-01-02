# Test with correct understanding - rotate 270 degrees
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Testing correct rotation for G.C.No extraction")
print("=" * 60)

# Get page 3
pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

# Rotate 270 degrees (slip is rotated 90 clockwise, so we rotate 270 to correct)
rotated = page.rotate(270, expand=True)
rotated.save(f"{save_dir}\\page3_rotated_270.png")
print("Saved page3_rotated_270.png")

# OCR
text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')

# Look for G.C.No pattern
print("\nSearching for G.C.No pattern...")
gc_pattern = r'G\.?C\.?\s*No\.?\s*[:\-]?\s*(\d{4,6})'
match = re.search(gc_pattern, text, re.IGNORECASE)

if match:
    print(f"FOUND: G.C.No.: {match.group(1)}")
else:
    print("Pattern not found directly. Checking all lines...")
    for line in text.split('\n'):
        if 'G' in line and 'C' in line and any(c.isdigit() for c in line):
            print(f"  Possible: {line}")

# Also search for just the number patterns
print("\nAll 5-digit numbers in text:")
numbers = re.findall(r'\b\d{5}\b', text)
print(numbers[:10])

print("\nOCR text (first 500 chars):")
print(text[:500])
