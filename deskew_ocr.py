# Try deskew approach on cropped GC number regions
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
from PIL import Image
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"


def deskew_image(img):
    """Deskew image using minAreaRect"""
    # Find all non-zero pixels
    coords = np.column_stack(np.where(img > 0))
    if len(coords) < 10:
        return img, 0
    
    # Get rotation angle
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    
    # Adjust angle
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    
    # Rotate
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated, angle


print("Deskew + OCR on failing pages")
print("=" * 60)

for page_num in [3, 5, 7, 17]:
    print(f"\n=== Page {page_num} ===")
    
    pages = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
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
            break
    
    if not gc_pos:
        print("  No G.C.No label found")
        continue
    
    print(f"  Label at ({gc_pos['x']}, {gc_pos['y']})")
    
    # Crop number region only (right of label)
    crop_x1 = gc_pos['x'] + gc_pos['w'] + 10
    crop_y1 = gc_pos['y'] - 30
    crop_x2 = min(rotated.width, crop_x1 + 400)
    crop_y2 = gc_pos['y'] + gc_pos['h'] + 30
    
    crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    
    # OpenCV processing
    img_np = np.array(crop)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # Binarize
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Deskew
    deskewed, angle = deskew_image(binary)
    print(f"  Deskew angle: {angle:.1f}")
    
    # Invert back for OCR (black text on white)
    deskewed_white = 255 - deskewed
    
    # Save images
    cv2.imwrite(f"{save_dir}\\page{page_num}_deskewed.png", deskewed_white)
    
    # OCR
    deskewed_pil = Image.fromarray(deskewed_white)
    
    for psm in [7, 8, 6]:
        text = pytesseract.image_to_string(
            deskewed_pil,
            config=f'--psm {psm} -c tessedit_char_whitelist=0123456789',
            lang='eng'
        ).strip()
        
        if text and len(text) >= 4:
            print(f"  PSM {psm}: {text}")
            break
    else:
        # Try without whitelist
        text = pytesseract.image_to_string(deskewed_pil, config='--psm 7', lang='eng')
        no_spaces = re.sub(r'\s', '', text)
        match = re.search(r'1\d{4}', no_spaces)
        if match:
            print(f"  Regex: {match.group(0)}")
        else:
            print(f"  Raw: {text.strip()[:30]}")

print("\n" + "=" * 60)
