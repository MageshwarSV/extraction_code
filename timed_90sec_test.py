# timed_90sec_test.py
"""
90-SECOND TIMEOUT TEST
If extraction takes >90 seconds, STOP and analyze why
"""
import sys, time, threading
from datetime import datetime
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

TIMEOUT_SECONDS = 90

print("="*70)
print("90-SECOND TIMEOUT TEST")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print("="*70)

# Convert image to PDF
img_path = r'C:/Users/avin4/.gemini/antigravity/brain/b37b3bb4-b7d3-4d29-a298-914b37c937f6/uploaded_image_1766340518811.jpg'

img = Image.open(img_path)
try:
    img = ImageOps.exif_transpose(img)
except:
    pass

MAX_DIM = 1700
w, h = img.size
if max(w, h) > MAX_DIM:
    scale = MAX_DIM / max(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    w, h = img.size

if img.mode != "RGB":
    img = img.convert("RGB")

quality = 85
img_buffer = io.BytesIO()
img.save(img_buffer, format='JPEG', quality=quality, optimize=True)

TARGET_SIZE = 300 * 1024
while img_buffer.tell() > TARGET_SIZE and quality > 60:
    quality -= 5
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG', quality=quality, optimize=True)

img_buffer.seek(0)

pdf_buffer = io.BytesIO()
c = canvas.Canvas(pdf_buffer, pagesize=(w, h))
img_reader = ImageReader(img_buffer)
c.drawImage(img_reader, 0, 0, width=w, height=h)
c.save()

test_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\test_90sec.pdf'
with open(test_pdf, 'wb') as f:
    f.write(pdf_buffer.getvalue())

print(f"PDF created: {len(pdf_buffer.getvalue())//1024}KB")
print(f"Image: {w}x{h}")

# Run extraction with timeout monitoring
print(f"\n[EXTRACTION TEST - 90 SECOND LIMIT]")
print(f"Start: {datetime.now().strftime('%H:%M:%S')}")

from engine.extractors.client1_format1 import run

extraction_done = False
result = None
error = None

def run_extraction():
    global result, error, extraction_done
    try:
        result = run(test_pdf)
        extraction_done = True
    except Exception as e:
        error = str(e)
        extraction_done = True

# Start extraction in thread
thread = threading.Thread(target=run_extraction)
start = time.time()
thread.start()

# Monitor with timeout
while thread.is_alive() and (time.time() - start) < TIMEOUT_SECONDS:
    elapsed = time.time() - start
    if int(elapsed) % 10 == 0 and int(elapsed) > 0:
        print(f"  ... {int(elapsed)}s elapsed (limit: {TIMEOUT_SECONDS}s)")
    time.sleep(1)

elapsed = time.time() - start

if thread.is_alive():
    print(f"\nTIMEOUT at {elapsed:.1f} seconds!")
    print(f"Extraction did NOT complete within {TIMEOUT_SECONDS} seconds")
    print("\nANALYSIS NEEDED:")
    print("  - Check what step is taking too long")
    print("  - Delivery address extraction?")
    print("  - Multiple OCR passes?")
    print("  - Image size/complexity?")
else:
    print(f"\nCompleted in {elapsed:.1f} seconds")
    if error:
        print(f"ERROR: {error}")
    elif result:
        print(f"Invoice: {result.get('Invoice No', 'NOT FOUND')}")
        print(f"Vehicle: {result.get('Vehicle', 'NOT FOUND')}")
        
        if elapsed <= TIMEOUT_SECONDS:
            print(f"\nSUCCESS: Extraction completed within {TIMEOUT_SECONDS}s limit!")
        else:
            print(f"\nFAILED: Took {elapsed:.1f}s (over {TIMEOUT_SECONDS}s limit)")

print("="*70)
