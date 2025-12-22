#!/usr/bin/env python3
"""
SCANNER-LIKE PREPROCESSING PIPELINE

Transform camera images to match scanner output characteristics:
1. Fix lighting uniformity
2. Enhance contrast
3. Sharpen
4. Denoise
5. Color balance/desaturation
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np
import cv2
import time

def apply_scanner_preprocessing(img):
    """
    Transform camera image to scanner-quality for faster OCR
    
    Args:
        img: PIL Image (camera-captured)
    
    Returns:
        PIL Image (scanner-like quality)
    """
    # Convert to numpy for OpenCV processing
    arr = np.array(img)
    
    # 1. FIX LIGHTING UNIFORMITY (biggest issue!)
    #    Scanner has uniform lighting, camera doesn't
    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # This fixes uneven lighting while preserving local contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    uniform = clahe.apply(gray)
    
    # 2. ENHANCE CONTRAST (make text stand out)
    #    Scanner output has high contrast
    # Use adaptive thresholding to enhance text
    contrast_enhanced = cv2.adaptiveThreshold(
        uniform, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,  # Larger block for documents
        C=10
    )
    
    # 3. DENOISE (remove camera sensor noise)
    #    Scanner has clean, noise-free output
    denoised = cv2.fastNlMeansDenoising(contrast_enhanced, None, h=10)
    
    # 4. SHARPEN (compensate for camera focus issues)
    #    Scanner has perfect focus
    kernel_sharpen = np.array([
        [-1, -1, -1],
        [-1,  9, -1],
        [-1, -1, -1]
    ])
    sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
    
    # 5. MORPHOLOGICAL CLEANUP (remove small artifacts)
    #    Scanner output is clean
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, kernel)
    
    # Convert back to PIL
    result_img = Image.fromarray(cleaned)
    
    return result_img


# TEST: Transform camera image and compare OCR speed
print("="*80)
print("TESTING SCANNER-LIKE PREPROCESSING")
print("="*80)

# Load camera-captured PDF
from pdf2image import convert_from_path
import pytesseract

poppler_bin = r"C:\poppler-25.07.0\Library\bin"
captured_pdf = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("\n[1] Loading camera-captured image...")
camera_img = convert_from_path(captured_pdf, dpi=200, poppler_path=poppler_bin)[0]
print(f"  Size: {camera_img.size}, Mode: {camera_img.mode}")

# Test 1: Original camera image
print("\n[2] OCR on ORIGINAL camera image...")
start = time.time()
text_original = pytesseract.image_to_string(camera_img, config='--psm 6')
time_original = time.time() - start
print(f"  Time: {time_original:.2f}s")
print(f"  Chars extracted: {len(text_original)}")

# Test 2: With scanner preprocessing
print("\n[3] Applying scanner-like preprocessing...")
start_prep = time.time()
scanner_like_img = apply_scanner_preprocessing(camera_img)
prep_time = time.time() - start_prep
print(f"  Preprocessing time: {prep_time:.2f}s")

# Save for visual comparison
scanner_like_img.save('camera_to_scanner.png')
print(f"  Saved 'camera_to_scanner.png'")

print("\n[4] OCR on SCANNER-LIKE preprocessed image...")
start = time.time()
text_preprocessed = pytesseract.image_to_string(scanner_like_img, config='--psm 6')
time_preprocessed = time.time() - start
print(f"  Time: {time_preprocessed:.2f}s")
print(f"  Chars extracted: {len(text_preprocessed)}")

# Results
print("\n" + "="*80)
print("RESULTS")
print("="*80)
total_original = time_original
total_preprocessed = prep_time + time_preprocessed

print(f"\nORIGINAL (camera):        {time_original:.2f}s OCR")
print(f"PREPROCESSED (scanner):   {prep_time:.2f}s prep + {time_preprocessed:.2f}s OCR = {total_preprocessed:.2f}s total")
print(f"\nSpeedup: {time_original/time_preprocessed:.2f}x OCR")
print(f"Overall: {total_original/total_preprocessed:.2f}x total")

if time_preprocessed < time_original * 0.5:
    print("\n*** SUCCESS! Scanner preprocessing makes OCR 2x+ FASTER! ***")
elif time_preprocessed < time_original * 0.8:
    print("\n** Good! Scanner preprocessing helps speed up OCR **")
else:
    print("\n* Preprocessing didn't help much - need to investigate further *")

print(f"\nAccuracy check:")
print(f"  Original extracted {len(text_original)} chars")
print(f"  Preprocessed extracted {len(text_preprocessed)} chars")
if abs(len(text_original) - len(text_preprocessed)) < 100:
    print(f"  Similar extraction (good!)")
else:
    print(f"  Different extraction (may have lost data)")
