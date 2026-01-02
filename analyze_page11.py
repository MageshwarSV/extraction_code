# Investigate Page 11 vehicle extraction issue
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\page11_analysis.txt"

print("=" * 70)
print("PAGE 11 VEHICLE ANALYSIS")
print("=" * 70 + "\n")

# Convert page 11
pages = convert_from_path(pdf_path, dpi=300, first_page=11, last_page=11)
page = pages[0]

# Get full OCR text
text = pytesseract.image_to_string(page, config='--psm 6', lang='eng')

print("Full OCR text for Page 11:")
print("-" * 50)
print(text)
print("-" * 50)

# Search for "vehicle" related lines
print("\n\nLines containing 'vehicle' or similar:")
lines = text.split('\n')
for i, line in enumerate(lines):
    line_lower = line.lower()
    if 'vehicle' in line_lower or 'veh' in line_lower or 'v6h' in line_lower:
        print(f"  Line {i}: {line}")

# Save to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("PAGE 11 VEHICLE ANALYSIS\n")
    f.write("=" * 70 + "\n\n")
    f.write("Full OCR Text:\n")
    f.write("-" * 50 + "\n")
    f.write(text)
    f.write("\n" + "-" * 50 + "\n")
    
    f.write("\n\nLines containing 'vehicle' or similar:\n")
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if 'vehicle' in line_lower or 'veh' in line_lower or 'v6h' in line_lower:
            f.write(f"  Line {i}: {line}\n")

print(f"\nAnalysis saved to: {output_file}")
