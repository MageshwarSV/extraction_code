# investigate_tesseract_slowdown.py
"""
Investigate why Tesseract is 8x slower on captured images vs PDFKSS
Compare the actual PIL images that Tesseract receives
"""
import sys
from pdf2image import convert_from_path
from PIL import Image
import numpy as np

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

poppler_bin = r"C:\poppler-25.07.0\Library\bin"

# Convert both PDFs to images
pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*70)
print("TESSERACT IMAGE COMPARISON")
print("="*70)

# PDFKSS image
print("\n[1] PDFKSS PDF -> Image (DPI 200)")
pdfkss_img = convert_from_path(pdfkss, dpi=200, poppler_path=poppler_bin)[0]
print(f"  Size: {pdfkss_img.size}")
print(f"  Mode: {pdfkss_img.mode}")
print(f"  Format: {pdfkss_img.format}")

# Convert to numpy to analyze
pdfkss_arr = np.array(pdfkss_img)
print(f"  NumPy shape: {pdfkss_arr.shape}")
print(f"  NumPy dtype: {pdfkss_arr.dtype}")
print(f"  Value range: {pdfkss_arr.min()} - {pdfkss_arr.max()}")
print(f"  Memory: {pdfkss_arr.nbytes // 1024 // 1024} MB")

# Captured image
print("\n[2] CAPTURED PDF -> Image (DPI 200)")
captured_img = convert_from_path(captured, dpi=200, poppler_path=poppler_bin)[0]
print(f"  Size: {captured_img.size}")
print(f"  Mode: {captured_img.mode}")
print(f"  Format: {captured_img.format}")

captured_arr = np.array(captured_img)
print(f"  NumPy shape: {captured_arr.shape}")
print(f"  NumPy dtype: {captured_arr.dtype}")
print(f"  Value range: {captured_arr.min()} - {captured_arr.max()}")
print(f"  Memory: {captured_arr.nbytes // 1024 // 1024} MB")

# Compare
print("\n[3] DIFFERENCES")
print("-"*70)
size_diff = (captured_img.size[0] * captured_img.size[1]) / (pdfkss_img.size[0] * pdfkss_img.size[1])
print(f"Pixel count ratio: {size_diff:.2f}x")
print(f"Mode match: {pdfkss_img.mode == captured_img.mode}")
print(f"Memory ratio: {(captured_arr.nbytes / pdfkss_arr.nbytes):.2f}x")

# Image stats
print("\n[4] IMAGE STATISTICS")
print("-"*70)
print(f"PDFKSS mean brightness: {pdfkss_arr.mean():.1f}")
print(f"Captured mean brightness: {captured_arr.mean():.1f}")

print(f"\nPDFKSS std dev: {pdfkss_arr.std():.1f}")
print(f"Captured std dev: {captured_arr.std():.1f}")

# Save samples for visual inspection
print("\n[5] SAVING SAMPLES")
pdfkss_img.save('pdfkss_sample.png')
captured_img.save('captured_sample.png')
print("  Saved: pdfkss_sample.png")
print("  Saved: captured_sample.png")

# Test Tesseract speed on both
print("\n[6] TESSERACT SPEED TEST")
print("-"*70)
import pytesseract
import time

print("Testing PDFKSS image...")
start = time.time()
text1 = pytesseract.image_to_string(pdfkss_img, config='--psm 6')
time1 = time.time() - start
print(f"  PDFKSS: {time1:.1f}s ({len(text1)} chars)")

print("Testing CAPTURED image...")
start = time.time()
text2 = pytesseract.image_to_string(captured_img, config='--psm 6')
time2 = time.time() - start
print(f"  CAPTURED: {time2:.1f}s ({len(text2)} chars)")

print(f"\n  Speed difference: {time2/time1:.1f}x slower")

print("\n" + "="*70)
print("CONCLUSION:")
if time2 > time1 * 2:
    print(f"  Captured image is {time2/time1:.1f}x SLOWER")
    print("  Likely causes:")
    if size_diff > 1.2:
        print(f"    - Image is {size_diff:.1f}x larger in pixels")
    if captured_arr.std() < pdfkss_arr.std() * 0.8:
        print("    - Image has lower contrast/detail")
    if captured_arr.mean() > pdfkss_arr.mean() * 1.2:
        print("    - Image is too bright")
else:
    print("  Both images process at similar speeds")
print("="*70)
