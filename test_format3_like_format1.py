# Test Format 3 with Format 1's OCR approach
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageOps, ImageFilter

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("Testing Format 3 with Format 1 OCR approach")
print("=" * 60)

# Convert page 2 at 300 DPI (like format1)
pages = convert_from_path(pdf_path, dpi=300, first_page=2, last_page=2)
page = pages[0]

print(f"Original size: {page.size}")

# STEP 1: Upscale 1.5x (like format1)
width, height = page.size
page_upscaled = page.resize((int(width * 1.5), int(height * 1.5)), Image.Resampling.LANCZOS)
print(f"Upscaled size: {page_upscaled.size}")

# STEP 2: Autocontrast grayscale
gray = ImageOps.autocontrast(page_upscaled.convert("L"))

# STEP 3: Sharpen
sharp = gray.filter(ImageFilter.UnsharpMask(radius=1.4, percent=140, threshold=3))

# Save processed image
sharp.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_processed.png")

# STEP 4: Try Format 1's OCR configs
cfgs = [
    r"--oem 1 --psm 6 -c preserve_interword_spaces=1",
    r"--oem 1 --psm 4 -c preserve_interword_spaces=1",
    r"--oem 1 --psm 3 -c preserve_interword_spaces=1",
    r"--oem 1 --psm 1 -c preserve_interword_spaces=1",
]

print("\nTrying OCR configs...")
for cfg in cfgs:
    try:
        txt = pytesseract.image_to_string(sharp, config=cfg, lang="eng") or ""
        print(f"\n{cfg[:20]}... : {len(txt)} chars")
        if txt.strip():
            print(f"  First 200: {txt[:200]}")
            break
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 60)
