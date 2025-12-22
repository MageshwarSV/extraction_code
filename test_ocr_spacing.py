import sys
import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import json

# Add project root to path
sys.path.append(os.getcwd())

# Test with pallipattu.pdf
pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\pallipattu.pdf"

print("Testing Tesseract with different configurations...")
print("=" * 80)

try:
    # Convert PDF to image
    images = convert_from_path(pdf_path, dpi=300)
    
    if images:
        img = images[0]
        
        # Test 1: Standard OCR
        print("\n1. Standard OCR (PSM 6):")
        text1 = pytesseract.image_to_string(img, config='--oem 1 --psm 6')
        print(text1[:500])
        
        # Test 2: Get detailed data with bounding boxes
        print("\n2. Detailed OCR data (checking character spacing):")
        data = pytesseract.image_to_data(img, config='--oem 1 --psm 6', output_type=pytesseract.Output.DICT)
        
        # Look for "TRS" or "T R S" pattern in the consignee area
        for i, text in enumerate(data['text']):
            if text and ('TRS' in text.upper() or 'SLT' in text.upper()):
                print(f"\nFound: '{text}'")
                print(f"  Position: ({data['left'][i]}, {data['top'][i]})")
                print(f"  Size: {data['width'][i]} x {data['height'][i]}")
                print(f"  Confidence: {data['conf'][i]}")
                
                # Check surrounding text for context
                if i > 0:
                    print(f"  Before: '{data['text'][i-1]}'")
                if i < len(data['text']) - 1:
                    print(f"  After: '{data['text'][i+1]}'")
        
        # Test 3: Character-level detection
        print("\n3. Character-level OCR:")
        char_data = pytesseract.image_to_boxes(img, config='--oem 1 --psm 6')
        print("First 500 chars of box data:")
        print(char_data[:500])
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
