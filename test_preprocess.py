# Try different preprocessing approaches
import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import cv2
import numpy as np
import re
import os

save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

# Test on image 0 (expected: 14549)
img_path = os.path.join(save_dir, "uploaded_image_0_1766600505138.png")
img = Image.open(img_path)

print("Testing different preprocessing on image 0 (expected: 14549)")
print("=" * 60)

# Method 1: Grayscale + Sharpen
print("\n1. Grayscale + Sharpen:")
gray = ImageOps.grayscale(img)
sharp = gray.filter(ImageFilter.SHARPEN)
text = pytesseract.image_to_string(sharp, config='--psm 6', lang='eng')
no_spaces = text.replace(' ', '').replace('\n', '')
print(f"   {text[:50]}... -> {re.findall(r'\\d{4,6}', no_spaces)}")

# Method 2: High contrast
print("\n2. High Contrast:")
gray = ImageOps.grayscale(img)
enhancer = ImageEnhance.Contrast(gray)
high_contrast = enhancer.enhance(3.0)
text = pytesseract.image_to_string(high_contrast, config='--psm 6', lang='eng')
no_spaces = text.replace(' ', '').replace('\n', '')
print(f"   {text[:50]}... -> {re.findall(r'\\d{4,6}', no_spaces)}")

# Method 3: Invert colors
print("\n3. Inverted:")
gray = ImageOps.grayscale(img)
inverted = ImageOps.invert(gray)
text = pytesseract.image_to_string(inverted, config='--psm 6', lang='eng')
no_spaces = text.replace(' ', '').replace('\n', '')
print(f"   {text[:50]}... -> {re.findall(r'\\d{4,6}', no_spaces)}")

# Method 4: Scale up 2x
print("\n4. Scale 2x:")
gray = ImageOps.grayscale(img)
scaled = gray.resize((gray.width * 2, gray.height * 2), Image.LANCZOS)
text = pytesseract.image_to_string(scaled, config='--psm 6', lang='eng')
no_spaces = text.replace(' ', '').replace('\n', '')
print(f"   {text[:50]}... -> {re.findall(r'\\d{4,6}', no_spaces)}")

# Method 5: Adaptive threshold
print("\n5. Adaptive Threshold:")
gray_np = np.array(ImageOps.grayscale(img))
adaptive = cv2.adaptiveThreshold(gray_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
adaptive_pil = Image.fromarray(adaptive)
text = pytesseract.image_to_string(adaptive_pil, config='--psm 6', lang='eng')
no_spaces = text.replace(' ', '').replace('\n', '')
print(f"   {text[:50]}... -> {re.findall(r'\\d{4,6}', no_spaces)}")

# Method 6: Morphological operations
print("\n6. Morphological (dilate+erode):")
gray_np = np.array(ImageOps.grayscale(img))
kernel = np.ones((2,2), np.uint8)
dilated = cv2.dilate(gray_np, kernel, iterations=1)
eroded = cv2.erode(dilated, kernel, iterations=1)
morph_pil = Image.fromarray(eroded)
text = pytesseract.image_to_string(morph_pil, config='--psm 6', lang='eng')
no_spaces = text.replace(' ', '').replace('\n', '')
print(f"   {text[:50]}... -> {re.findall(r'\\d{4,6}', no_spaces)}")

print("\n" + "=" * 60)
