# Test Format 3 - RAW without ANY preprocessing
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Format 3 - RAW OCR (no preprocessing)")
print("=" * 60)

# Convert page 2
pages = convert_from_path(pdf_path, dpi=300, first_page=2, last_page=2)
page = pages[0]  # Keep as RGB color

print(f"Image mode: {page.mode}")  # Should be RGB
print(f"Image size: {page.size}")

# OCR with Format 1's config but on COLOR image
cfg = "--oem 1 --psm 6 -c preserve_interword_spaces=1"
text = pytesseract.image_to_string(page, config=cfg, lang="eng")

print(f"\nOCR result length: {len(text)} chars")
if len(text) > 50:
    print("\nFirst 300 chars:")
    print(text[:300])
    print("\n[SUCCESS] Tesseract extracted text!")
else:
    print("[FAILED] No text extracted")
    
    # Try alternative approach - save and OCR from file
    print("\nTrying save-and-load approach...")
    save_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_test_color.png"
    page.save(save_path)
    text2 = pytesseract.image_to_string(save_path, config=cfg, lang="eng")
    print(f"From file: {len(text2)} chars")
    if len(text2) > 50:
        print(text2[:300])
