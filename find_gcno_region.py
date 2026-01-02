# Check if G.C.No is in the image by cropping different parts
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

pages = convert_from_path(pdf_path, dpi=300, first_page=3, last_page=3)  # Higher DPI
page = pages[0]
rotated = page.rotate(90, expand=True)

w, h = rotated.size
print(f"Rotated image size: {w}x{h}")

# The G.C.No box is on the right side of original = bottom of rotated image
# Crop bottom part (where G.C.No should be)
bottom_region = rotated.crop((0, int(h*0.6), w, h))
bottom_region.save(f"{save_dir}\\page3_bottom_region.png")

# Also crop right part
right_region = rotated.crop((int(w*0.6), 0, w, h))
right_region.save(f"{save_dir}\\page3_right_region.png")

print("OCR on bottom region (where G.C.No should be):")
print("-" * 40)
text_bottom = pytesseract.image_to_string(bottom_region, config='--psm 6', lang='eng')
print(text_bottom[:800])

# Look for G.C.No pattern
gc_match = re.search(r'G\.?C\.?\s*No\.?\s*[:\.\-]?\s*(\d{4,6})', text_bottom, re.IGNORECASE)
if gc_match:
    print(f"\nFOUND G.C.No: {gc_match.group(1)}")
else:
    # Look for any 5-digit numbers
    numbers = re.findall(r'\b\d{5}\b', text_bottom)
    print(f"\n5-digit numbers in bottom: {numbers}")

print("\n\nOCR on right region:")
print("-" * 40)
text_right = pytesseract.image_to_string(right_region, config='--psm 6', lang='eng')
gc_match2 = re.search(r'G\.?C\.?\s*No\.?\s*[:\.\-]?\s*(\d{4,6})', text_right, re.IGNORECASE)
if gc_match2:
    print(f"FOUND G.C.No: {gc_match2.group(1)}")
numbers2 = re.findall(r'\b\d{5}\b', text_right)
print(f"5-digit numbers in right: {numbers2}")
