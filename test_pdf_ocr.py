from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Testing PDF to Image + OCR...")
print(f"PDF: {pdf_path}\n")

# Convert page 2 (known invoice page)
print("Converting page 2...")
pages = convert_from_path(pdf_path, dpi=200, first_page=2, last_page=2)
page = pages[0]

print(f"Image size: {page.size}")
print(f"Image mode: {page.mode}")

# Save for inspection
save_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\test_pdf_page2.png"
page.save(save_path)
print(f"Saved to: test_pdf_page2.png\n")

# Try OCR with different configs
configs = [
    ('Default', ''),
    ('PSM 3', '--psm 3'),
    ('PSM 6', '--psm 6'),
    ('PSM 11', '--psm 11'),
]

print("Testing OCR with different PSM modes:")
print("=" * 60)

for name, config in configs:
    text = pytesseract.image_to_string(page, config=config)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    print(f"\n{name} ({config or 'none'}):")
    print(f"  Characters: {len(text)}")
    print(f"  Lines: {len(lines)}")
    if lines:
        print(f"  First 3 lines: {lines[:3]}")
    else:
        print(f"  ❌ NO TEXT EXTRACTED")

print("\n" + "=" * 60)
