# Try all rotations and find G.C.No
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Finding G.C.No with correct rotation")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=200, first_page=3, last_page=3)
page = pages[0]

for angle in [0, 90, 180, 270]:
    rotated = page.rotate(angle, expand=True)
    rotated.save(f"{save_dir}\\page3_rot{angle}.png")
    
    text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    
    # Look for G.C.No
    gc_match = re.search(r'G\.?C\.?\s*No\.?\s*[:\.\-]?\s*(\d{4,6})', text, re.IGNORECASE)
    
    # Also look for 5-digit numbers
    five_digit = re.findall(r'\b\d{5}\b', text)
    
    print(f"\n{angle} degrees:")
    if gc_match:
        print(f"  G.C.No FOUND: {gc_match.group(1)}")
    
    if five_digit:
        print(f"  5-digit numbers: {five_digit[:5]}")
    
    # Check for readable text markers
    if 'CONSIGNMENT' in text.upper():
        print("  [✓] CONSIGNMENT found")
    if 'ROADWAYS' in text.upper():
        print("  [✓] ROADWAYS found")
    if 'KSS' in text.upper():
        print("  [✓] KSS found")

print("\n" + "=" * 60)
