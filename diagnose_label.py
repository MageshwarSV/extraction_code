"""
Diagnostic: What does Tesseract see at rotation 180?
"""
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
import re

PDF_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\ilovepdf_merged (2).pdf"

def diagnose():
    print("Loading PDF...")
    pages = convert_from_path(PDF_PATH, dpi=300)
    page = pages[0]  # First page (Consignment)
    
    # Rotate to 180
    rotated = page.rotate(180, expand=True)
    print(f"Page size after 180: {rotated.size}")
    
    # Top 50%
    top_h = int(rotated.height * 0.5)
    top_region = rotated.crop((0, 0, rotated.width, top_h))
    
    print(f"Top region size: {top_region.size}")
    
    # OCR with data output
    data = pytesseract.image_to_data(top_region, config='--psm 6', output_type=Output.DICT)
    
    print("\n=== All detected text (with positions) ===")
    for i, text in enumerate(data['text']):
        if text and text.strip():
            # Check if this matches our pattern
            match = re.search(r'(G\.?C\.?N|5\.?C\.?N|6\.?C\.?N|G\.?C\.?No|GC\s*No)', text, re.IGNORECASE)
            marker = " <<< MATCH!" if match else ""
            print(f"  [{i}] '{text}' at x={data['left'][i]}, y={data['top'][i]}, conf={data['conf'][i]}{marker}")
    
    print("\n=== Full text dump ===")
    full_text = pytesseract.image_to_string(top_region, config='--psm 6')
    print(full_text[:1500])

if __name__ == "__main__":
    diagnose()
