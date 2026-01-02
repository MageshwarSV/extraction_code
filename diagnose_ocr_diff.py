"""
Diagnostic Script: Compare Windows vs Docker PDF Rendering
This script investigates WHY OCR results differ between Windows and Docker.

The hypothesis is that Poppler (PDF -> Image) renders fonts differently on
Windows vs Linux, causing Tesseract to see different pixels.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# ============================================================
# CONFIGURATION
# ============================================================
PDF_PATH = "uploads/vehcileprob.pdf"  # The problematic PDF
OUTPUT_DIR = Path("diagnostic_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Detect Tesseract
TESSERACT_PATHS = [
    r"C:\Tesseract-OCR\tesseract.exe",  # Windows
    "/usr/bin/tesseract",  # Linux/Docker
]
for p in TESSERACT_PATHS:
    if os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        print(f"[INFO] Using Tesseract: {p}")
        break

# Detect Poppler
POPPLER_PATHS = [
    r"C:\poppler-25.07.0\Library\bin",  # Windows
    None,  # Linux (system path)
]
poppler_path = None
for p in POPPLER_PATHS:
    if p is None or os.path.exists(p):
        poppler_path = p
        print(f"[INFO] Using Poppler: {p or 'System PATH'}")
        break

# ============================================================
# STEP 1: Render PDF to Image
# ============================================================
print("\n" + "="*60)
print("STEP 1: Rendering PDF to Image")
print("="*60)

images = convert_from_path(
    PDF_PATH,
    dpi=300,
    poppler_path=poppler_path
)

# Save rendered image
page1 = images[0]
rendered_path = OUTPUT_DIR / "rendered_page1.png"
page1.save(rendered_path)
print(f"[INFO] Saved rendered image: {rendered_path}")
print(f"[INFO] Image size: {page1.size}")
print(f"[INFO] Image mode: {page1.mode}")

# ============================================================
# STEP 2: Crop the DESTINATION region specifically
# ============================================================
print("\n" + "="*60)
print("STEP 2: Cropping DESTINATION Region")
print("="*60)

# The destination field is typically in the upper-middle area
# Let's crop a region that should contain "KOVILAMBAKKAM"
# Based on typical invoice layout, destination is around y=600-800

width, height = page1.size
# Approximate destination region (adjust if needed)
dest_region = (
    int(width * 0.5),   # left 50%
    int(height * 0.15), # top 15%
    int(width * 0.85),  # right 85%
    int(height * 0.25)  # bottom 25%
)

dest_crop = page1.crop(dest_region)
dest_crop_path = OUTPUT_DIR / "destination_region.png"
dest_crop.save(dest_crop_path)
print(f"[INFO] Saved destination region: {dest_crop_path}")
print(f"[INFO] Crop coordinates: {dest_region}")

# ============================================================
# STEP 3: Run OCR on the destination region
# ============================================================
print("\n" + "="*60)
print("STEP 3: OCR on Destination Region")
print("="*60)

# Get OCR text
ocr_text = pytesseract.image_to_string(dest_crop, config="--psm 6")
print(f"[INFO] OCR Result:\n{ocr_text}")

# Check for KOVIL vs KOVFL
if "KOVIL" in ocr_text.upper():
    print("\n✓ CORRECT: Found 'KOVIL' in OCR output")
elif "KOVFL" in ocr_text.upper():
    print("\n✗ ERROR: Found 'KOVFL' instead of 'KOVIL' - This is the Linux/Docker bug!")
else:
    print("\n? Neither KOVIL nor KOVFL found in this region")

# ============================================================
# STEP 4: Get Tesseract version info
# ============================================================
print("\n" + "="*60)
print("STEP 4: Environment Information")
print("="*60)

import platform
print(f"[INFO] OS: {platform.system()} {platform.release()}")
print(f"[INFO] Python: {sys.version}")

try:
    tess_version = pytesseract.get_tesseract_version()
    print(f"[INFO] Tesseract Version: {tess_version}")
except Exception as e:
    print(f"[WARN] Could not get Tesseract version: {e}")

# Also get detailed character-level OCR data
print("\n" + "="*60)
print("STEP 5: Character-Level OCR Analysis")
print("="*60)

# Get character-level data to see confidence scores
try:
    data = pytesseract.image_to_data(dest_crop, output_type=pytesseract.Output.DICT, config="--psm 6")
    
    # Find words containing "KOV"
    for i, word in enumerate(data['text']):
        if word and 'KOV' in word.upper():
            print(f"[FOUND] Word: '{word}' | Confidence: {data['conf'][i]}%")
            print(f"        Position: ({data['left'][i]}, {data['top'][i]}) | Size: {data['width'][i]}x{data['height'][i]}")
except Exception as e:
    print(f"[ERROR] Character analysis failed: {e}")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
print(f"\nCheck the images in: {OUTPUT_DIR.absolute()}")
print("Compare 'rendered_page1.png' between Windows and Docker to see pixel differences.")
