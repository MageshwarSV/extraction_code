"""
Vehicle Number OCR Comparison: Windows vs Docker
This script specifically targets the Vehicle Number field to find the root cause.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# ============================================================
# CONFIGURATION
# ============================================================
PDF_PATH = "uploads/vehcileprob.pdf"
OUTPUT_DIR = Path("vehicle_diagnostic")
OUTPUT_DIR.mkdir(exist_ok=True)

# Detect Tesseract
TESSERACT_PATHS = [
    r"C:\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
]
for p in TESSERACT_PATHS:
    if os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        print(f"[INFO] Tesseract: {p}")
        break

# Detect Poppler
POPPLER_PATHS = [
    r"C:\poppler-25.07.0\Library\bin",
    None,
]
poppler_path = None
for p in POPPLER_PATHS:
    if p is None or os.path.exists(p):
        poppler_path = p
        print(f"[INFO] Poppler: {p or 'System PATH'}")
        break

# Get environment info
import platform
print(f"[INFO] OS: {platform.system()} {platform.release()}")

try:
    tess_version = pytesseract.get_tesseract_version()
    print(f"[INFO] Tesseract Version: {tess_version}")
except:
    pass

# ============================================================
# STEP 1: Render PDF
# ============================================================
print("\n" + "="*60)
print("STEP 1: Rendering PDF")
print("="*60)

images = convert_from_path(PDF_PATH, dpi=300, poppler_path=poppler_path)
page1 = images[0]
page1.save(OUTPUT_DIR / "full_page.png")
print(f"[INFO] Page size: {page1.size}")

# ============================================================
# STEP 2: Locate and crop Vehicle Number region
# ============================================================
print("\n" + "="*60)
print("STEP 2: Cropping Vehicle Number Region")
print("="*60)

# Vehicle number is typically in the middle-left area of invoices
# Let's search for it in the full text first
full_text = pytesseract.image_to_string(page1, config="--psm 6")

# Find "Vehicle" in text to locate the region
vehicle_lines = [line for line in full_text.split('\n') if 'Vehicle' in line or 'Wagon' in line]
print(f"[INFO] Lines containing 'Vehicle':")
for line in vehicle_lines[:5]:
    print(f"       {line[:100]}")

# Get word-level bounding boxes to find Vehicle Number location
data = pytesseract.image_to_data(page1, output_type=pytesseract.Output.DICT, config="--psm 6")

# Find the word "Vehicle" and get its position
vehicle_positions = []
for i, word in enumerate(data['text']):
    if word and ('Vehicle' in word or 'Wagon' in word):
        vehicle_positions.append({
            'word': word,
            'left': data['left'][i],
            'top': data['top'][i],
            'width': data['width'][i],
            'height': data['height'][i],
            'conf': data['conf'][i]
        })

print(f"\n[INFO] Found {len(vehicle_positions)} 'Vehicle/Wagon' occurrences:")
for pos in vehicle_positions[:5]:
    print(f"       '{pos['word']}' at ({pos['left']}, {pos['top']}) conf={pos['conf']}%")

# Crop around the first Vehicle occurrence
if vehicle_positions:
    pos = vehicle_positions[0]
    # Crop a wider region to capture the full vehicle number
    left = max(0, pos['left'] - 50)
    top = max(0, pos['top'] - 20)
    right = min(page1.width, pos['left'] + 600)  # Vehicle numbers are ~400-500px wide
    bottom = min(page1.height, pos['top'] + 80)
    
    vehicle_crop = page1.crop((left, top, right, bottom))
    vehicle_crop.save(OUTPUT_DIR / "vehicle_region.png")
    print(f"\n[INFO] Cropped region: ({left}, {top}, {right}, {bottom})")
    
    # ============================================================
    # STEP 3: OCR specifically on Vehicle region
    # ============================================================
    print("\n" + "="*60)
    print("STEP 3: OCR on Vehicle Region")
    print("="*60)
    
    # Try multiple PSM modes
    for psm in [6, 7, 8, 11, 13]:
        ocr_result = pytesseract.image_to_string(vehicle_crop, config=f"--psm {psm}").strip()
        print(f"[PSM {psm:2d}] {ocr_result[:80]}")
    
    # Character-level analysis
    print("\n" + "="*60)
    print("STEP 4: Character-Level Confidence Analysis")
    print("="*60)
    
    char_data = pytesseract.image_to_data(vehicle_crop, output_type=pytesseract.Output.DICT, config="--psm 7")
    
    for i, word in enumerate(char_data['text']):
        if word and len(word) > 5 and any(c.isdigit() for c in word):
            print(f"[WORD] '{word}' | Confidence: {char_data['conf'][i]}%")
            # This could be the vehicle number

# ============================================================
# STEP 5: Full page text search for vehicle pattern
# ============================================================
print("\n" + "="*60)
print("STEP 5: Regex Search for Vehicle Number Pattern")
print("="*60)

import re
# Look for Indian vehicle number patterns: XX00XX0000 or similar
patterns = [
    r'[A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{4}',  # TN 19 F 6397
    r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}',  # TN19F6397
    r'KA\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{4}',  # KA specific
]

for pattern in patterns:
    matches = re.findall(pattern, full_text.replace('\n', ' '))
    if matches:
        print(f"[PATTERN] {pattern}")
        for m in matches[:5]:
            print(f"          Found: '{m}'")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
print(f"\nImages saved to: {OUTPUT_DIR.absolute()}")
