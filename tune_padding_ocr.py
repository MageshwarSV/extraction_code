import cv2
import numpy as np
import pytesseract
import os

IMG_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_WINNER_padded.png"

def tune_ocr(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        # Try finding the rot180 one if padded logic was internal
        path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_WINNER_rot180.png"
    
    print(f"Tuning OCR on: {os.path.basename(path)}")
    img = cv2.imread(path)
    
    # 1. Scaling Factors
    scales = [2, 3, 4]
    
    # 2. Morph Operations
    morphs = [
        ("None", None),
        ("Erode-1", (cv2.erode, 1)),
        ("Dilate-1", (cv2.dilate, 1)), # Logic: Dilate might close the loop of '9' if it's broken and looking like '3'
        ("Dilate-2", (cv2.dilate, 2)),
    ]
    
    # 3. PSM Modes
    psms = [6, 7, 8, 13]
    
    found_any = False
    
    for scale in scales:
        # Pre-scale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Grid Search
        for m_name, m_op in morphs:
            processed = scaled.copy()
            if m_op:
                func, iters = m_op
                kernel = np.ones((2,2), np.uint8) # Small kernel
                processed = func(processed, kernel, iterations=iters)
            
            # Thresholding (Standard)
            _, thresh = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Inversion (checking both black-on-white and white-on-black)
            variants = [("Normal", thresh), ("Inverted", cv2.bitwise_not(thresh))]
            
            for v_name, v_img in variants:
                for psm in psms:
                    config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
                    text = pytesseract.image_to_string(v_img, config=config).strip()
                    
                    if "14549" in text:
                        print(f"✅ SUCCESS: [Scale {scale}x | {m_name} | {v_name} | PSM {psm}] -> '{text}'")
                        found_any = True
                    elif "1454" in text:
                         print(f"   Close:   [Scale {scale}x | {m_name} | {v_name} | PSM {psm}] -> '{text}'")

    if not found_any:
        print("❌ No perfect match found in grid search.")

if __name__ == "__main__":
    tune_ocr(IMG_PATH)
