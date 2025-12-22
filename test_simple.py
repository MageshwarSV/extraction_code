# test_simple.py
import os
from PIL import Image
import subprocess

img_path = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766332921501.jpg'
output_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_capture.pdf'
output_with_ocr = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_capture_ocr.pdf'

print("Processing image...")

# Load and resize
img = Image.open(img_path)
w, h = img.size
MAX_DIM = 1700

if max(w, h) > MAX_DIM:
    scale = MAX_DIM / max(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

if img.mode != "RGB":
    img = img.convert("RGB")

print(f"Image size: {img.size}")

# Save as JPEG with quality to get under 300KB
quality = 85
img.save('temp_img.jpg', format='JPEG', quality=quality, optimize=True)
size_kb = os.path.getsize('temp_img.jpg') // 1024

while size_kb > 300 and quality > 50:
    quality -= 5
    img.save('temp_img.jpg', format='JPEG', quality=quality, optimize=True)
    size_kb = os.path.getsize('temp_img.jpg') // 1024

print(f"JPEG quality: {quality}, Size: {size_kb} KB")

# Convert to PDF using img2pdf (simpler than reportlab)
import img2pdf
with open(output_pdf, 'wb') as f:
    f.write(img2pdf.convert('temp_img.jpg'))

pdf_size = os.path.getsize(output_pdf) // 1024
print(f"PDF created: {pdf_size} KB")

# Add OCR text layer
print("Adding OCR text layer...")
result = subprocess.run([
    'ocrmypdf',
    '--language', 'eng',
    '--force-ocr',
    '--optimize', '1',
    '--tesseract-config', '--oem 1 --psm 3',
    output_pdf,
    output_with_ocr
], capture_output=True, timeout=180)

if result.returncode == 0:
    final_size = os.path.getsize(output_with_ocr) // 1024
    print(f"OCR PDF created: {final_size} KB")
    
    # Check text layer
    import fitz
    doc = fitz.open(output_with_ocr)
    text = doc[0].get_text()
    print(f"Text layer: {len(text)} chars")
    print("Sample:", text[:200])
else:
    print("OCR failed:", result.returncode)

os.remove('temp_img.jpg')
