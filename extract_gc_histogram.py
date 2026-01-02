import cv2
import numpy as np
import pytesseract
import os
# import matplotlib.pyplot as plt

# Target Image
IMG_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_WINNER_rot180.png" 
# Use padded version as it might help histogram start/end cleanly

def extract_digits_via_histogram(path):
    if not os.path.exists(path):
        print(f"Image not found: {path}")
        return

    print(f"Processing: {os.path.basename(path)}")
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Threshold (Invert: Text=White, BG=Black)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 2. Vertical Projection (Sum columns)
    # Axis 0 = sum down the rows (leaving columns)
    v_hist = np.sum(thresh, axis=0) / 255 # Normalize to pixel count
    
    # 3. Find Gaps (where sum is near zero or local minima)
    # We expect 5 peaks (digits) and 4 valleys.
    
    # Simple logic: If val > 0, we are in a char. If val == 0, we are in a gap.
    in_char = False
    starts = []
    ends = []
    
    for i, val in enumerate(v_hist):
        if val > 0 and not in_char:
            in_char = True
            starts.append(i)
        elif val == 0 and in_char:
            in_char = False
            ends.append(i)
            
    if in_char: # Close last char
        ends.append(len(v_hist))
        
    # FORCE SPLIT if fewer than 5 segments found (Logic for "14549" -> 5 digits)
    if len(starts) < 5:
        print(f"Only {len(starts)} segments found. Attempting Valley Split...")
        # Smooth the histogram to find reliable valleys
        # Simple moving average
        kernel_size = 5
        kernel = np.ones(kernel_size) / kernel_size
        smooth_hist = np.convolve(v_hist, kernel, mode='same')
        
        # Find local minima
        # We look for "Deepest Valleys" that are spaced appropriately
        # Expected width per digit ~ W / 5
        width = img.shape[1]
        approx_digit_w = width // 5
        
        # Find indices where (val < left) and (val < right)
        # Scan for valleys
        valleys = []
        for i in range(5, len(smooth_hist)-5):
            if smooth_hist[i] < smooth_hist[i-1] and smooth_hist[i] < smooth_hist[i+1]:
                valleys.append(i)
                
        # Filter valleys to avoid noise (must be somewhat spaced)
        # Select 4 valleys that best divide the image into 5?
        # Or just take evenly spaced cuts if valleys match?
        
        # Let's try simple "cut at approx_digit_w intervals adjusted to nearest valley"
        starts = []
        ends = []
        
        current_x = 0
        for i in range(5):
             # Target end = current_x + approx_digit_w
             target = current_x + approx_digit_w
             
             # Search for valley near target (+- 20px)
             best_cut = target
             min_val = float('inf')
             
             search_start = max(current_x + 10, target - 20)
             search_end = min(width - 5, target + 20)
             
             if i == 4: # Last digit takes remaining
                 best_cut = width
             else:
                 for x in range(int(search_start), int(search_end)):
                     if smooth_hist[x] < min_val:
                         min_val = smooth_hist[x]
                         best_cut = x
             
             starts.append(current_x)
             ends.append(best_cut)
             current_x = best_cut

    print(f"Found {len(starts)} potential segments.")
    
    # Visualization
    viz_img = img.copy()
    
    extracted_text = ""
    
    for i, (s, e) in enumerate(zip(starts, ends)):
        w = e - s
        if w < 5: continue # Too thin (noise)
        
        # Add padding to segment
        pad = 5
        x1 = max(0, s - pad)
        x2 = min(img.shape[1], e + pad)
        
        # Crop
        roi = gray[:, x1:x2]
        
        # Invert for Tesseract (Black on White) implies standard image is already B on W?
        # Check: standard Threshold was INV+OTSU -> Text White.
        # So 'gray' is original -> Text Dark?
        # Tesseract likes Dark text on White bg.
        # Assuming original is standard scan.
        
        # OCR
        # PSM 10 = Single Character
        char = pytesseract.image_to_string(roi, config='--psm 10 -c tessedit_char_whitelist=0123456789').strip()
        print(f"  Segment {i}: x={s}..{e} (w={w}) -> OCR: '{char}'")
        
        extracted_text += char
        
        # Draw on viz
        cv2.rectangle(viz_img, (s, 0), (e, img.shape[0]), (0, 255, 0), 2)
        
    print(f"\nFinal Histogram Extraction: {extracted_text}")
    
    cv2.imwrite("debug_histogram_viz.jpg", viz_img)
    print("Saved debug_histogram_viz.jpg")

if __name__ == "__main__":
    extract_digits_via_histogram(IMG_PATH)
