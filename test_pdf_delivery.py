
import sys
import os
import cv2
import numpy as np
from pdf2image import convert_from_path
import shutil

# Setup paths
sys.path.append(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")
from engine.extractors.odsfhiaclient1_format11_format1 import extract_delivery_address_robust

def test_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print(f"Processing PDF: {pdf_path}")
    
    # Check for Poppler
    if not shutil.which("pdftoppm"):
        print("WARNING: 'pdftoppm' not found in PATH.")
        # Try common locations
        common_paths = [
            r"C:\Program Files\poppler-24.02.0\Library\bin",
            r"C:\Program Files\poppler-0.68.0\bin",
            r"C:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\poppler\bin"
        ]
        for p in common_paths:
            if os.path.exists(p):
                print(f"Found poppler at: {p}")
                os.environ["PATH"] += os.pathsep + p
                break
    
    try:
        # Convert first page to image
        # Don't pass poppler_path explicitly if we added it to PATH or if it's already there
        images = convert_from_path(pdf_path, dpi=300)
        if not images:
            print("Failed to convert PDF to images.")
            return
            
        page_image = images[0] # Page 1
        
        # Run extraction
        # Note: page_num=1 is used for naming the debug file
        result = extract_delivery_address_robust(page_image, page_num=1, debug=True)
        
        print("\n" + "="*40)
        print("EXTRACTION RESULT:")
        print("="*40)
        print(result)
        print("="*40)
        
        # Check debug crop
        debug_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_debug_f1"
        crop_path = os.path.join(debug_dir, "page_1_delivery_robust.png")
        if os.path.exists(crop_path):
            print(f"\nDebug crop saved at: {crop_path}")
        else:
            print(f"\nDebug crop path not found at {crop_path}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    target_pdf = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\6978029188.pdf"
    test_pdf(target_pdf)
