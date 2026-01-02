# OpenCV contour-based digit extraction - save output to file
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
output_path = f"{save_dir}\\opencv_extract_results.txt"

with open(output_path, 'w') as f:
    f.write("OpenCV Contour-Based Digit Extraction\n")
    f.write("=" * 60 + "\n\n")
    
    # Test on page 7 (should be 14519)
    pages = convert_from_path(pdf_path, dpi=200, first_page=7, last_page=7)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        if 'G.C' in word.upper() or 'GC' in word.upper():
            gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
            f.write(f"G.C.No label found at ({gc_pos['x']}, {gc_pos['y']})\n")
            break
    
    if gc_pos:
        # Crop the number area
        crop_x1 = gc_pos['x'] + gc_pos['w'] + 10
        crop_y1 = gc_pos['y'] - 50
        crop_x2 = min(rotated.width, crop_x1 + 400)
        crop_y2 = gc_pos['y'] + gc_pos['h'] + 50
        
        crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        crop.save(f"{save_dir}\\page7_number_crop.png")
        f.write(f"Saved crop: {crop.size}\n")
        
        # OpenCV processing
        img_np = np.array(crop)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        f.write(f"Found {len(contours)} contours\n")
        
        # Filter by size
        digit_contours = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if 15 < h < 100 and 5 < w < 80:
                digit_contours.append((x, y, w, h))
        
        digit_contours.sort(key=lambda c: c[0])
        f.write(f"Filtered to {len(digit_contours)} digit candidates\n\n")
        
        # Extract each digit
        digits = ""
        for i, (x, y, w, h) in enumerate(digit_contours):
            pad = 5
            x1, y1 = max(0, x - pad), max(0, y - pad)
            x2, y2 = min(binary.shape[1], x + w + pad), min(binary.shape[0], y + h + pad)
            
            digit_img = binary[y1:y2, x1:x2]
            digit_img = 255 - digit_img
            
            digit_pil = Image.fromarray(digit_img)
            digit_text = pytesseract.image_to_string(
                digit_pil, 
                config='--psm 10 -c tessedit_char_whitelist=0123456789',
                lang='eng'
            ).strip()
            
            f.write(f"Contour {i}: ({x}, {y}) size=({w}x{h}) -> '{digit_text}'\n")
            if digit_text and digit_text.isdigit():
                digits += digit_text
        
        f.write(f"\nExtracted number: {digits}\n")
        f.write(f"Expected: 14519\n")
        
        # Save annotated
        img_annotated = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        for (x, y, w, h) in digit_contours:
            cv2.rectangle(img_annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imwrite(f"{save_dir}\\page7_contours.png", img_annotated)

print(f"Results saved to: {output_path}")
