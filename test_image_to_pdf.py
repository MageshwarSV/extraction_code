# test_image_to_pdf.py
"""
Test creating PDF from uploaded image with:
1. Color preservation (no grayscale)
2. Accurate OCR text layer
3. File size < 300KB
"""
import os
import sys
from PIL import Image
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

# Input image
img_path = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766332921501.jpg'
output_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_capture.pdf'
output_with_ocr = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_capture_ocr.pdf'

print("=" * 70)
print("TESTING: Image → PDF with Text Layer")
print("=" * 70)

# Load image
img = Image.open(img_path)
print(f"\n[1] Original Image:")
print(f"    Size: {img.size}")
print(f"    Mode: {img.mode}")
print(f"    File size: {os.path.getsize(img_path)//1024} KB")

# Resize to 1700px max (like PDFKSS)
MAX_DIM = 1700
w, h = img.size
if max(w, h) > MAX_DIM:
    scale = MAX_DIM / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    print(f"    Resized to: {img.size}")

# Keep color (RGB)
if img.mode != "RGB":
    img = img.convert("RGB")

# Create PDF with image
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=(img.width, img.height))

# Compress image to JPEG with quality adjustment to stay under 300KB
quality = 85
img_buffer = io.BytesIO()
img.save(img_buffer, format='JPEG', quality=quality, optimize=True)

# Reduce quality if needed to stay under 300KB
TARGET_SIZE = 300 * 1024  # 300KB
while img_buffer.tell() > TARGET_SIZE and quality > 50:
    quality -= 5
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG', quality=quality, optimize=True)

img_buffer.seek(0)
print(f"\n[2] Image Compression:")
print(f"    JPEG Quality: {quality}")
print(f"    Compressed size: {img_buffer.tell()//1024} KB")

# Draw image on PDF
img_reader = ImageReader(img_buffer)
c.drawImage(img_reader, 0, 0, width=img.width, height=img.height)
c.save()

# Save PDF without text layer first
pdf_bytes = pdf_buffer.getvalue()
with open(output_pdf, 'wb') as f:
    f.write(pdf_bytes)
print(f"\n[3] PDF Created (no text layer):")
print(f"    File: {output_pdf}")
print(f"    Size: {len(pdf_bytes)//1024} KB")

# Add OCR text layer using ocrmypdf with better accuracy settings
print(f"\n[4] Adding OCR Text Layer...")
import subprocess

result = subprocess.run([
    'ocrmypdf',
    '--language', 'eng',
    '--force-ocr',
    '--deskew',
    '--rotate-pages',
    '--optimize', '1',
    '--jobs', '4',
    '--tesseract-config', '--oem 1 --psm 3 -c preserve_interword_spaces=1',
    output_pdf,
    output_with_ocr
], capture_output=True, text=True, timeout=180)

if result.returncode == 0 and os.path.exists(output_with_ocr):
    final_size = os.path.getsize(output_with_ocr) // 1024
    print(f"    ✓ OCR completed!")
    print(f"    File: {output_with_ocr}")
    print(f"    Size: {final_size} KB")
    
    # Extract text layer and compare
    print(f"\n[5] Text Layer Verification:")
    import fitz
    doc = fitz.open(output_with_ocr)
    text_layer = doc[0].get_text()
    doc.close()
    
    print(f"    Text layer length: {len(text_layer)} chars")
    print(f"\n    First 500 chars:")
    print("    " + "-" * 60)
    print("    " + text_layer[:500].replace('\n', '\n    '))
    print("    " + "-" * 60)
    
    # Check for key fields from the invoice
    checks = {
        'Invoice No': 'L269' in text_layer or '269' in text_layer,
        'GSTIN': '33AA' in text_layer or 'GSTIN' in text_layer,
        'UltraTech': 'ULTRATECH' in text_layer.upper() or 'ULTRA' in text_layer.upper(),
        'Vehicle': 'TN18' in text_layer or 'VEHICLE' in text_layer.upper(),
    }
    
    print(f"\n[6] Accuracy Check:")
    for field, found in checks.items():
        status = "✓" if found else "✗"
        print(f"    {status} {field}: {'Found' if found else 'NOT FOUND'}")
    
else:
    print(f"    ✗ OCR failed: {result.stderr}")

print("\n" + "=" * 70)
