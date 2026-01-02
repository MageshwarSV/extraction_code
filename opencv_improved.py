# OpenCV digit extraction - improved with morphological operations
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
from PIL import Image

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Improved OpenCV Digit Extraction")
print("=" * 60)

# Page 7
pages = convert_from_path(pdf_path, dpi=300, first_page=7, last_page=7)  # Higher DPI
page = pages[0]
rotated = page.rotate(90, expand=True)

# Find G.C.No
data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)

gc_pos = None
for i, word in enumerate(data['text']):
    if not word:
        continue
    if 'G.C' in word.upper() or 'GC' in word.upper():
        gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
        print(f"Label at ({gc_pos['x']}, {gc_pos['y']})")
        break

if gc_pos:
    # Wider crop for the number
    crop_x1 = gc_pos['x'] + gc_pos['w'] - 20
    crop_y1 = gc_pos['y'] - 80
    crop_x2 = min(rotated.width, crop_x1 + 600)
    crop_y2 = gc_pos['y'] + gc_pos['h'] + 80
    
    crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    crop.save(f"{save_dir}\\page7_crop_v2.png")
    
    img_np = np.array(crop)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # Try adaptive thresholding for better binarization
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5)
    cv2.imwrite(f"{save_dir}\\page7_binary_v2.png", binary)
    
    # Morphological operations to clean up
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.erode(binary, kernel, iterations=1)
    binary = cv2.dilate(binary, kernel, iterations=1)
    cv2.imwrite(f"{save_dir}\\page7_morph_v2.png", binary)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Found {len(contours)} contours")
    
    # Filter - at 300 DPI, digits are larger
    digit_contours = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0
        area = cv2.contourArea(cnt)
        
        # Digits: height 30-150px, width 10-100px, aspect ratio 0.2-1.0
        if 30 < h < 150 and 10 < w < 100 and 0.2 < aspect < 1.0 and area > 200:
            digit_contours.append((x, y, w, h))
            print(f"  Candidate: ({x}, {y}) size={w}x{h} aspect={aspect:.2f} area={area}")
    
    digit_contours.sort(key=lambda c: c[0])
    print(f"Filtered to {len(digit_contours)} digit candidates")
    
    # Extract digits
    digits = ""
    for (x, y, w, h) in digit_contours:
        pad = 8
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(binary.shape[1], x + w + pad)
        y2 = min(binary.shape[0], y + h + pad)
        
        digit_img = 255 - binary[y1:y2, x1:x2]
        
        digit_pil = Image.fromarray(digit_img)
        text = pytesseract.image_to_string(
            digit_pil,
            config='--psm 10 -c tessedit_char_whitelist=0123456789',
            lang='eng'
        ).strip()
        
        if text.isdigit():
            digits += text
    
    print(f"\nExtracted: {digits}")
    print(f"Expected: 14519")
    
    # Save annotated
    img_annotated = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    for (x, y, w, h) in digit_contours:
        cv2.rectangle(img_annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
    cv2.imwrite(f"{save_dir}\\page7_contours_v2.png", img_annotated)

print("=" * 60)
