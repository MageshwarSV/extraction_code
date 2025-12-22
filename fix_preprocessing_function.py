#!/usr/bin/env python3
"""
Fix the broken client1_format1.py file
Find and rebuild the corrupted _preprocess_variants_fast function
"""

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

print("Reading broken file...")
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Find the broken function
start_idx = None
for i, line in enumerate(lines):
    if 'def _preprocess_variants_fast(' in line:
        start_idx = i
        break

if start_idx is None:
    print("ERROR: Could not find _preprocess_variants_fast function!")
    exit(1)

print(f"Found function at line {start_idx + 1}")

# Find the end of the function (next def or class)
end_idx = None
for i in range(start_idx + 1, len(lines)):
    if lines[i].startswith('def ') or lines[i].startswith('class '):
        end_idx = i
        break

if end_idx is None:
    print("ERROR: Could not find end of function!")
    exit(1)

print(f"Function ends at line {end_idx + 1}")
print(f"Replacing {end_idx - start_idx} lines...")

# The correct, complete function
fixed_function = '''def _preprocess_variants_fast(img: Image.Image, is_captured_image: bool = False) -> List[Image.Image]:
    """Create preprocessed image variants for better OCR - enhanced for tilted text AND spaced initials"""
    img = _rotate_upright(img)
    
    # OPTIMIZATION: Skip upscaling for captured images (already high quality)
    if not is_captured_image:
        # Upscale image for better character recognition (especially for spaced letters)
        # Increase resolution by 1.5x to help Tesseract detect spaces between letters
        width, height = img.size
        img = img.resize((int(width * 1.5), int(height * 1.5)), Image.Resampling.LANCZOS)
    
    # For captured images: Apply SCANNER-LIKE preprocessing for faster OCR
    if is_captured_image:
        # Convert to numpy for OpenCV processing
        import cv2
        import numpy as np
        
        arr = np.array(img)
        
        # Convert to grayscale
        if len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr
        
        # 1. FIX LIGHTING UNIFORMITY (biggest speed issue!)
        # Apply CLAHE for uniform brightness (like scanner)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        uniform = clahe.apply(gray)
        
        # 2. ENHANCE CONTRAST (make text stand out like scanner)
        # Using adaptive thresholding
        contrast_enhanced = cv2.adaptiveThreshold(
            uniform, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=21,  # Large block for documents
            C=10
        )
        
        # 3. DENOISE (remove camera sensor noise)
        denoised = cv2.fastNlMeansDenoising(contrast_enhanced, None, h=10)
        
        # 4. SHARPEN (compensate for camera focus issues)
        kernel_sharpen = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
        
        # 5. MORPHOLOGICAL CLEANUP (remove artifacts)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL
        scanner_like = Image.fromarray(cleaned)
        return [scanner_like]  # Single variant, scanner-quality
    
    # Variant 1: Autocontrast grayscale
    g = ImageOps.autocontrast(img.convert("L"))
    
    # Variant 2: Sharpened version
    sharp = g.filter(ImageFilter.UnsharpMask(radius=1.4, percent=140, threshold=3))
    
    # Variant 3: Enhanced contrast and noise reduction for tilted text
    enhanced = g.copy()
    # Apply morphological operations to clean up text
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV format
        cv_img = np.array(enhanced)
        
        # Apply adaptive thresholding for better text separation
        # Use larger block size to preserve character spacing
        thresh = cv2.adaptiveThreshold(cv_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2)
        
        # IMPORTANT: Use minimal morphological operations to preserve spacing
        # Smaller kernel to avoid merging spaced characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL
        enhanced = Image.fromarray(morph)
    except ImportError:
        # If OpenCV not available, use PIL operations
        enhanced = ImageOps.autocontrast(enhanced)
        enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))  # Noise reduction
    
    return [g, sharp, enhanced]


'''

# Replace the broken function
new_lines = lines[:start_idx] + [fixed_function] + lines[end_idx:]

# Write fixed file
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ File fixed!")

# Verify syntax
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', filepath], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print("✅ Syntax check PASSED!")
else:
    print("❌ Syntax check FAILED:")
    print(result.stderr)
