import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
import os

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\debug"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def get_header_points(image_cv):
    data = pytesseract.image_to_data(image_cv, config='--psm 6', output_type=pytesseract.Output.DICT)
    points = []
    for i in range(len(data['text'])):
        text = data['text'][i].lower().strip()
        if 'recip' in text or 'consign' in text:
            print(f"Match: '{text}' at x={data['left'][i]}, y={data['top'][i]}, conf={data['conf'][i]}")
            if data['conf'][i] > 30:
                points.append({
                    'x': data['left'][i] + data['width'][i] // 2,
                    'y': data['top'][i] + data['height'][i] // 2,
                    'left': data['left'][i],
                    'right': data['left'][i] + data['width'][i]
                })
    if not points: return None
    avg_y = np.median([p['y'] for p in points])
    line_points = [p for p in points if abs(p['y'] - avg_y) < 25]
    return sorted(line_points, key=lambda p: p['x'])

def piecewise_deskew(image, points, target_y=20, crop_height=200): # Larger height for debug
    xs = [p['x'] for p in points]
    ys = [p['y'] for p in points]
    (h, w) = image.shape[:2]
    map_x = np.zeros((crop_height, w), np.float32)
    map_y = np.zeros((crop_height, w), np.float32)
    for x in range(w):
        if x <= xs[0]: local_y = ys[0]
        elif x >= xs[-1]: local_y = ys[-1]
        else:
            for i in range(len(xs)-1):
                if xs[i] <= x <= xs[i+1]:
                    ratio = (x - xs[i]) / (xs[i+1] - xs[i])
                    local_y = ys[i] + ratio * (ys[i+1] - ys[i])
                    break
        for cy in range(crop_height):
            map_x[cy, x] = x
            map_y[cy, x] = local_y + (cy - target_y)
    return cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def debug_page(page_num):
    pages = convert_from_path(pdf_path, dpi=300, first_page=page_num, last_page=page_num)
    page = pages[0]
    img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]
    search_y1, search_y2 = int(height * 0.15), int(height * 0.45)
    search_x1, search_x2 = int(width * 0.40), int(width * 0.98)
    search_area = img_cv[search_y1:search_y2, search_x1:search_x2]
    
    header_points = get_header_points(search_area)
    if header_points:
        straightened = piecewise_deskew(search_area, header_points, target_y=20, crop_height=300)
        cv2.imwrite(os.path.join(output_dir, f"page_{page_num}_full_strip.png"), straightened)
        print(f"Saved full strip for Page {page_num}")
    else:
        print(f"Header not found for Page {page_num}")

if __name__ == "__main__":
    debug_page(4)
