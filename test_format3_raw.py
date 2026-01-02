# Test Format 3 PDF - raw OCR without any preprocessing
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from PIL import Image

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("FORMAT 3 RAW OCR TEST")
print("=" * 60)

# Convert page 2
pages = convert_from_path(pdf_path, dpi=300, first_page=2, last_page=2)  # Try 300 DPI
page = pages[0]

print(f"Page size: {page.size}, Mode: {page.mode}")

# Convert to RGB if needed
if page.mode != 'RGB':
    page = page.convert('RGB')
    print("Converted to RGB")

# Save for inspection
page.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_raw_300dpi.png")

# Try OCR with default settings (no PSM)
text = pytesseract.image_to_string(page)
print(f"\nOCR length: {len(text)} chars")

if len(text) > 50:
    print("First 500 chars:")
    print(text[:500])
    
    # Check for key markers
    if 'INVOICE' in text.upper():
        print("\n[OK] Found INVOICE marker")
    if 'DATE' in text.upper():
        print("[OK] Found DATE marker")
    if 'POST' in text.upper():
        print("[OK] Found POST marker")
else:
    print("FAILED - No text extracted")
    print("Trying alternative: Convert to grayscale + high contrast")
    
    # Try grayscale
    gray = page.convert('L')
    text2 = pytesseract.image_to_string(gray)
    print(f"Grayscale OCR length: {len(text2)} chars")
    if len(text2) > 50:
        print("First 300 chars:", text2[:300])
