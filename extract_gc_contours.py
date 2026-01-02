import cv2
import numpy as np
import pytesseract
import os

# Target the image the user said "I can see 14549" in
IMG_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_WINNER_rot180.png"

def extract_digits_via_contours(path):
    if not os.path.exists(path):
        print(f"Image not found: {path}")
        return

    print(f"Processing: {os.path.basename(path)}")
    img = cv2.imread(path)
    
    # 1. Preprocessing
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Upscale heavily to separate characters
    scale = 4
    scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # Thresholding
    _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # EROSION to separate connected characters
    kernel = np.ones((5,5), np.uint8)
    thresh = cv2.erode(thresh, kernel, iterations=2)
    print("Applied Erosion (Kernel 5x5, 2 iters)")
    
    # Check if we need to invert (we want white digits on black background for contours)
    # The above assumes black text on white bg -> THRESH_BINARY_INV makes text white.
    
    # 2. Find Contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 3. Filter Contours (Keep only digit-like shapes)
    digit_candidates = []
    viz_img = cv2.cvtColor(scaled, cv2.COLOR_GRAY2BGR)
    
    height, width = scaled.shape
    min_h = height * 0.4  # Digit must be at least 40% of image height
    max_h = height * 0.95 
    min_w = 10 * scale    # Min width in pixels
    
    print(f"Detected {len(contours)} contours. Filtering...")
    
    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        print(f"  Contour {i}: x={x}, y={y}, w={w}, h={h} (img_h={height})")
        
        # Filter noise (RELAXED)
        if h < height * 0.15: # < 15% height is probably noise
             continue 
        
        # Store
        digit_candidates.append((x, y, w, h, cnt))
        
        # Draw all candidates in Blue
        cv2.rectangle(viz_img, (x, y), (x+w, y+h), (255, 0, 0), 2)

    # 4. Sort Left to Right
    digit_candidates.sort(key=lambda c: c[0])
    
    # 5. Extract and OCR each
    full_number = ""
    
    print(f"Found {len(digit_candidates)} valid digit candidates.")
    
    for i, (x, y, w, h, cnt) in enumerate(digit_candidates):
        # Draw final chosen in Green
        cv2.rectangle(viz_img, (x, y), (x+w, y+h), (0, 255, 0), 4)
        
        # Add padding for safe OCR
        pad = 10
        roi = scaled[max(0, y-pad):min(height, y+h+pad), max(0, x-pad):min(width, x+w+pad)]
        
        # Invert back to Black Text on White (Tesseract prefers this)
        roi = cv2.bitwise_not(roi)
        
        # OCR Single Char
        char = pytesseract.image_to_string(roi, config='--psm 10 -c tessedit_char_whitelist=0123456789').strip()
        print(f"  Digit {i+1}: char='{char}' (w={w}, h={h})")
        
        if char:
            full_number += char
        else:
            # Fallback: Count pixel density?
            pass

    print(f"\nFinal Extracted Number: {full_number}")
    
    # Save visualization
    out_path = "debug_contours_viz.jpg"
    cv2.imwrite(out_path, viz_img)
    print(f"Saved visualization to: {out_path}")

if __name__ == "__main__":
    extract_digits_via_contours(IMG_PATH)
