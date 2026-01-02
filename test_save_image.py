from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Converting page 2...")
pages = convert_from_path(pdf_path, dpi=200, first_page=2, last_page=2)
page = pages[0]

# Save image
save_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\test_page2.png"
page.save(save_path)
print(f"Saved to: {save_path}")
print(f"Image size: {page.size}")
print(f"Image mode: {page.mode}")

# Try OCR
text = pytesseract.image_to_string(page)
print(f"\nOCR result length: {len(text)}")
print(f"First 500 chars:\n{text[:500]}")
