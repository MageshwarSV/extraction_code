# Final improved OpenCV extraction - all output to file
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
output_file = f"{save_dir}\\opencv_final_results.txt"

results = []

for page_num in [3, 5, 7, 17]:  # Failing pages
    pages = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
    page = pages[0]
    rotated = page.rotate(90, expand=True)
    
    data = pytesseract.image_to_data(rotated, config='--psm 6', lang='eng', output_type=Output.DICT)
    
    gc_pos = None
    for i, word in enumerate(data['text']):
        if not word:
            continue
        if 'G.C' in word.upper() or 'GC' in word.upper():
            gc_pos = {'x': data['left'][i], 'y': data['top'][i], 'w': data['width'][i], 'h': data['height'][i]}
            break
    
    if not gc_pos:
        results.append((page_num, None, "No G.C.No label"))
        continue
    
    # Crop
    crop_x1 = gc_pos['x'] + gc_pos['w'] - 20
    crop_y1 = gc_pos['y'] - 100
    crop_x2 = min(rotated.width, crop_x1 + 600)
    crop_y2 = gc_pos['y'] + gc_pos['h'] + 100
    
    crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    
    img_np = np.array(crop)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # Adaptive threshold
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5)
    
    # Morphological
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.erode(binary, kernel, iterations=1)
    binary = cv2.dilate(binary, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter
    digit_contours = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0
        area = cv2.contourArea(cnt)
        
        if 30 < h < 150 and 10 < w < 100 and 0.2 < aspect < 1.0 and area > 200:
            digit_contours.append((x, y, w, h))
    
    digit_contours.sort(key=lambda c: c[0])
    
    # Extract
    digits = ""
    for (x, y, w, h) in digit_contours:
        pad = 8
        x1, y1 = max(0, x-pad), max(0, y-pad)
        x2, y2 = min(binary.shape[1], x+w+pad), min(binary.shape[0], y+h+pad)
        
        digit_img = 255 - binary[y1:y2, x1:x2]
        digit_pil = Image.fromarray(digit_img)
        
        text = pytesseract.image_to_string(
            digit_pil,
            config='--psm 10 -c tessedit_char_whitelist=0123456789',
            lang='eng'
        ).strip()
        
        if text.isdigit():
            digits += text
    
    results.append((page_num, digits if digits else None, f"{len(digit_contours)} contours"))

# Write results
with open(output_file, 'w') as f:
    f.write("OpenCV Contour Extraction Results\n")
    f.write("=" * 50 + "\n\n")
    
    expected = {3: "14516", 5: "14531", 7: "14519", 17: "14511"}
    
    for page_num, extracted, note in results:
        exp = expected.get(page_num, "?")
        status = "OK" if extracted == exp else "DIFF"
        f.write(f"Page {page_num:2}: Extracted={extracted or '-':>8}  Expected={exp}  {status}  ({note})\n")

print(f"Results saved to: {output_file}")
