"""
Direct OCR Comparison: Windows vs Docker
Uses the EXACT same OCR logic as client1_format1.py
"""
import sys
import os
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

# Import the ACTUAL functions from client1_format1.py
from engine.extractors.odsfhiaclient1_format11_format1 import (
    _detect_tesseract,
    _detect_poppler,
    _preprocess_variants_fast,
    _ocr_configs_fast,
    _merge_text,
    extract_vehicle,
    extract_destination,
    clean_destination,
)
from pdf2image import convert_from_path
import platform

# ============================================================
# CONFIGURATION
# ============================================================
PDF_PATH = "uploads/vehcileprob.pdf"

print("=" * 60)
print("OCR COMPARISON TEST - Using client1_format1.py Logic")
print("=" * 60)

# Detect environment
print(f"\n[ENV] OS: {platform.system()} {platform.release()}")
print(f"[ENV] Python: {sys.version.split()[0]}")

# Detect tools
tess = _detect_tesseract(None)
print(f"[ENV] Tesseract: {tess}")

poppler = _detect_poppler(None)
print(f"[ENV] Poppler: {poppler or 'System PATH'}")

# ============================================================
# STEP 1: Render PDF (same as client1_format1.py)
# ============================================================
print("\n" + "=" * 60)
print("STEP 1: Rendering PDF at DPI 300")
print("=" * 60)

if poppler:
    pages = convert_from_path(PDF_PATH, dpi=300, poppler_path=poppler)
else:
    pages = convert_from_path(PDF_PATH, dpi=300)

print(f"[INFO] Rendered {len(pages)} page(s)")

# ============================================================
# STEP 2: Run OCR (same as client1_format1.py)
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: Running OCR with _preprocess_variants_fast + _ocr_configs_fast")
print("=" * 60)

all_blocks = []
for pg_num, pg in enumerate(pages, 1):
    print(f"[INFO] Processing page {pg_num}...")
    
    # Exact same preprocessing as client1_format1.py
    variants = _preprocess_variants_fast(pg)
    page_texts = []
    
    for v in variants:
        page_texts.extend(_ocr_configs_fast(v))
    
    merged = _merge_text(page_texts) if page_texts else ""
    all_blocks.append(merged)

# Combine all page text
full_text = "\n".join(all_blocks)
print(f"[INFO] Total OCR text length: {len(full_text)} characters")

# ============================================================
# STEP 3: Extract Vehicle Number
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: Extracting Vehicle Number")
print("=" * 60)

# Find lines containing "Vehicle" to see raw OCR
vehicle_lines = [l for l in full_text.split('\n') if 'Vehicle' in l or 'Wagon' in l or 'vehicle' in l]
print(f"[RAW OCR] Lines containing 'Vehicle/Wagon':")
for line in vehicle_lines[:10]:
    print(f"    {line[:100]}")

# Now extract using the actual function
vehicle_result = extract_vehicle(full_text, pages)
print(f"\n[EXTRACTED] Vehicle No: {vehicle_result}")

# ============================================================
# STEP 4: Extract Destination
# ============================================================
print("\n" + "=" * 60)
print("STEP 4: Extracting Destination")
print("=" * 60)

# Find lines containing destination keywords
dest_lines = [l for l in full_text.split('\n') if 'Destination' in l or 'DESTINATION' in l or 'destination' in l]
print(f"[RAW OCR] Lines containing 'Destination':")
for line in dest_lines[:10]:
    print(f"    {line[:100]}")

# Now extract using the actual function
dest_result = extract_destination(full_text)
print(f"\n[RAW EXTRACTED] Destination: {dest_result}")

# Apply cleaning
if dest_result:
    cleaned_dest = clean_destination(dest_result)
    print(f"[CLEANED] Destination: {cleaned_dest}")

# ============================================================
# STEP 5: Save full OCR text for comparison
# ============================================================
print("\n" + "=" * 60)
print("STEP 5: Saving Full OCR Text")
print("=" * 60)

output_dir = Path("ocr_comparison")
output_dir.mkdir(exist_ok=True)

# Save based on platform
if platform.system() == "Windows":
    output_file = output_dir / "ocr_windows.txt"
else:
    output_file = output_dir / "ocr_docker.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f"[SAVED] Full OCR text to: {output_file}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
