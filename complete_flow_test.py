# complete_flow_test.py
"""
COMPLETE FLOW TEST:
1. Load uploaded image
2. Convert to PDF using NEW upload_routes.py method
3. Extract from it
4. Compare with PDFKSS
"""
import sys, time
from datetime import datetime
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

print("="*70)
print("COMPLETE FLOW TEST: Image -> PDF -> Extraction")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print("="*70)

# STEP 1: Convert uploaded image to PDF (NEW METHOD)
print("\n[STEP 1] Converting uploaded image to PDF (NEW upload_routes.py method)")
img_path = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766340050068.jpg'

# Load image
img = Image.open(img_path)
print(f"  Original: {img.size}, {img.mode}")

# Fix rotation using EXIF
try:
    img = ImageOps.exif_transpose(img)
except:
    pass

# Resize to 1700px max
MAX_DIM = 1700
w, h = img.size
if max(w, h) > MAX_DIM:
    scale = MAX_DIM / max(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    w, h = img.size
    print(f"  Resized: {img.size}")

# Keep color (RGB)
if img.mode != "RGB":
    img = img.convert("RGB")

# Compress JPEG to <300KB
TARGET_SIZE = 300 * 1024
quality = 85
img_buffer = io.BytesIO()
img.save(img_buffer, format='JPEG', quality=quality, optimize=True)

while img_buffer.tell() > TARGET_SIZE and quality > 60:
    quality -= 5
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG', quality=quality, optimize=True)

img_buffer.seek(0)
jpeg_kb = img_buffer.tell() // 1024
print(f"  Compressed: {jpeg_kb}KB (quality={quality})")

# Create PDF (no text layer)
pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=(w, h))
img_reader = ImageReader(img_buffer)
c.drawImage(img_reader, 0, 0, width=w, height=h)
c.save()

pdf_bytes = pdf_buffer.getvalue()
captured_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploaded_captured.pdf'
with open(captured_pdf, 'wb') as f:
    f.write(pdf_bytes)

pdf_kb = len(pdf_bytes) // 1024
print(f"  PDF created: {pdf_kb}KB")
print(f"  Saved to: uploaded_captured.pdf")

# STEP 2: Extract from captured image PDF
print(f"\n[STEP 2] Extracting from CAPTURED IMAGE PDF")
print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")

from engine.extractors.odsfhiaclient1_format11_format1 import run

start = time.time()
result_captured = run(captured_pdf)
time_captured = time.time() - start

print(f"  End: {datetime.now().strftime('%H:%M:%S')}")
print(f"  TIME: {time_captured:.1f}s ({time_captured/60:.1f}min)")
print(f"  Invoice: {result_captured.get('Invoice No', 'NOT FOUND')}")
print(f"  Vehicle: {result_captured.get('Vehicle', 'NOT FOUND')}")

# STEP 3: Extract from PDFKSS (for comparison)
print(f"\n[STEP 3] Extracting from PDFKSS (for comparison)")
pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")

start = time.time()
result_pdfkss = run(pdfkss)
time_pdfkss = time.time() - start

print(f"  End: {datetime.now().strftime('%H:%M:%S')}")
print(f"  TIME: {time_pdfkss:.1f}s ({time_pdfkss/60:.1f}min)")
print(f"  Invoice: {result_pdfkss.get('Invoice No', 'NOT FOUND')}")

# COMPARISON
print("\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\nPDF Creation (upload_routes.py):")
print(f"  Image size: {w}x{h}")
print(f"  JPEG: {jpeg_kb}KB (quality={quality})")
print(f"  PDF: {pdf_kb}KB")

print(f"\nExtraction Times:")
print(f"  CAPTURED IMAGE: {time_captured:.1f}s ({time_captured/60:.1f}min)")
print(f"  PDFKSS:         {time_pdfkss:.1f}s ({time_pdfkss/60:.1f}min)")
print(f"  Difference:     {abs(time_captured-time_pdfkss):.1f}s")

if time_captured <= time_pdfkss * 1.5:
    print(f"\nSUCCESS: Captured image extraction is comparable to PDFKSS!")
    print("New upload_routes.py approach WORKS!")
else:
    print(f"\nWARNING: Captured image is {(time_captured/time_pdfkss-1)*100:.0f}% slower")

print(f"\nCompleted: {datetime.now().strftime('%H:%M:%S')}")
print("="*70)
