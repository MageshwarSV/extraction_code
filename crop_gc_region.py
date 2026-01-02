"""
Script 1: Rotation + Cropping
- Loads PDF
- Finds the consignment page
- Rotates to find "G.C.No" label  
- Crops the GC number region
- Saves as 'gc_cropped.png' for Script 2
"""
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
from PIL import Image, ImageOps
import cv2
import numpy as np
import re
import os

PDF_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\ilovepdf_merged (2).pdf"
OUTPUT_CROP = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_cropped.png"

def find_label_and_crop(page_pil):
    """
    Try rotations to find G.C.No label and crop the number region.
    Returns cropped PIL image or None.
    """
    
    for rotation in [180, 90, 270, 0]:
        print(f"  Trying rotation {rotation}...")
        rotated = page_pil.rotate(rotation, expand=True)
        
        # Scan top 50%
        top_h = int(rotated.height * 0.5)
        top_region = rotated.crop((0, 0, rotated.width, top_h))
        
        # OCR to find label
        data = pytesseract.image_to_data(top_region, config='--psm 6', output_type=Output.DICT)
        
        for i, text in enumerate(data['text']):
            if not text:
                continue
            
            # Check for G.C.No pattern
            if re.search(r'(G\.?C\.?N|5\.?C\.?N|6\.?C\.?N|G\.?C\.?No|GC\s*No)', text, re.IGNORECASE):
                print(f"  [FOUND] Label '{text}' at rotation {rotation}")
                
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # Crop region (to the RIGHT of the label)
                crop_x1 = x + w + 5  # Start just after the label
                crop_y1 = max(0, y - 60)
                crop_x2 = min(top_region.width, x + w + 700)
                crop_y2 = y + h + 80
                
                # Perform crop
                roi = top_region.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                
                # Add white padding (helps edge character detection)
                roi = ImageOps.expand(roi, border=20, fill='white')
                
                print(f"  Cropped region size: {roi.size}")
                return roi, rotation
        
        print(f"  Label not found at rotation {rotation}")
    
    return None, None

def main():
    print("=" * 50)
    print("STEP 1: ROTATION + CROPPING")
    print("=" * 50)
    
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        return
    
    print(f"Loading: {os.path.basename(PDF_PATH)}")
    pages = convert_from_path(PDF_PATH, dpi=300)
    
    for i, page in enumerate(pages):
        print(f"\n--- Page {i+1} ---")
        
        # Quick type check
        text = pytesseract.image_to_string(page.rotate(180, expand=True), config='--psm 6')
        if "CONSIGNMENT" not in text.upper():
            print("  Not a consignment page, skipping")
            continue
        
        print("  Type: CONSIGNMENT")
        
        # Find label and crop
        cropped, rotation = find_label_and_crop(page)
        
        if cropped:
            cropped.save(OUTPUT_CROP)
            print(f"\n[SUCCESS] Saved cropped region to: {OUTPUT_CROP}")
            print(f"  Rotation used: {rotation}")
            print(f"  Now run: python extract_from_crop.py")
            return  # Exit after first success
        else:
            print("  [FAILED] Could not find G.C.No label in any rotation")

if __name__ == "__main__":
    main()
