# Debug page 7 - should be 14519
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Debug Page 7 - Expected: 14519")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=200, first_page=7, last_page=7)
page = pages[0]
rotated = page.rotate(90, expand=True)

# Save full page
rotated.save(f"{save_dir}\\page7_full.png")

data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

# Show all G.C related words
print("G.C related words:")
for i, word in enumerate(data['text']):
    if not word:
        continue
    if 'G.C' in word.upper() or 'GC' in word.upper():
        print(f"  '{word}' at ({data['left'][i]}, {data['top'][i]})")

# Show all words with digits near expected area
print("\nAll words with digits:")
for i, word in enumerate(data['text']):
    if not word:
        continue
    digits = re.sub(r'\D', '', word)
    if len(digits) >= 2:  # At least 2 digits
        x = data['left'][i]
        y = data['top'][i]
        print(f"  '{word}' -> '{digits}' at ({x}, {y})")

# Full text search for 14519
print("\nFull text search for '14519':")
full_text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
if '14519' in full_text:
    print("  FOUND in full text!")
else:
    # Check spaced version
    if '1 4 5 1 9' in full_text or '145 19' in full_text:
        print("  Found spaced version")
    else:
        # Look for 145 and 19 separately
        if '145' in full_text and '19' in full_text:
            print("  Found 145 and 19 separately")
        else:
            print("  NOT found, searching for fragments...")
            # Find all 5-digit sequences
            no_spaces = full_text.replace(' ', '').replace('\n', '')
            matches = re.findall(r'1\d{4}', no_spaces)
            print(f"  5-digit starting with 1: {matches}")

print("=" * 60)
