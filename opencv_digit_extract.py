# OpenCV contour-based digit extraction
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
from PIL import Image, ImageOps
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("OpenCV Contour-Based Digit Extraction")
print("=" * 60)

# Test on page 7 (should be 14519)
pages = convert_from_path(pdf_path, dpi=200, first_page=7, last_page=7)
page = pages[0]
rotated = page.rotate(90, expand=True)

# Find G.C.No label position
data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    if 'G.C' in word.upper() or 'GC' in word.upper():
        gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
        print(f"G.C.No label found at ({gc_pos['x']}, {gc_pos['y']})")
        break

if gc_pos:
    # Crop the number area (to the right of label)
    crop_x1 = gc_pos['x'] + gc_pos['w'] + 10  # Start after label
    crop_y1 = gc_pos['y'] - 50
    crop_x2 = min(rotated.width, crop_x1 + 400)  # Wide enough for number
    crop_y2 = gc_pos['y'] + gc_pos['h'] + 50
    
    crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    crop.save(f"{save_dir}\\page7_number_crop.png")
    print(f"Saved crop: {crop.size}")
    
    # Convert to OpenCV format
    img_np = np.array(crop)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # Binarize
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"Found {len(contours)} contours")
    
    # Filter contours by size (digits should be certain height)
    digit_contours = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # Digits should be reasonable size
        if 15 < h < 100 and 5 < w < 80:
            digit_contours.append((x, y, w, h))
    
    # Sort by X position (left to right)
    digit_contours.sort(key=lambda c: c[0])
    
    print(f"Filtered to {len(digit_contours)} digit candidates")
    
    # Extract and OCR each digit
    digits = ""
    for i, (x, y, w, h) in enumerate(digit_contours):
        # Add padding
        pad = 5
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(binary.shape[1], x + w + pad)
        y2 = min(binary.shape[0], y + h + pad)
        
        digit_img = binary[y1:y2, x1:x2]
        
        # Invert for OCR (white background, black text)
        digit_img = 255 - digit_img
        
        # OCR this single digit
        digit_pil = Image.fromarray(digit_img)
        digit_text = pytesseract.image_to_string(
            digit_pil, 
            config='--psm 10 -c tessedit_char_whitelist=0123456789',
            lang='eng'
        ).strip()
        
        if digit_text and digit_text.isdigit():
            digits += digit_text
            print(f"  Contour {i}: ({x}, {y}) -> '{digit_text}'")
    
    print(f"\nExtracted number: {digits}")
    print(f"Expected: 14519")
    
    # Save annotated image
    img_annotated = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    for (x, y, w, h) in digit_contours:
        cv2.rectangle(img_annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
    cv2.imwrite(f"{save_dir}\\page7_contours.png", img_annotated)
    print(f"Saved annotated image with contours")

print("=" * 60)
