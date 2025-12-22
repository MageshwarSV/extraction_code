import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee
from pdf2image import convert_from_path
import pytesseract

# Path to the PDF
pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\pallipattu.pdf"

print(f"Processing: {pdf_path}")
print("=" * 80)

try:
    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=300)
    print(f"✓ Converted PDF to {len(images)} image(s)")
    
    if images:
        # Get OCR text from first page
        print("\nPerforming OCR...")
        ocr_text = pytesseract.image_to_string(images[0])
        
        print("\n" + "=" * 80)
        print("OCR TEXT (first 1000 chars):")
        print("=" * 80)
        print(ocr_text[:1000])
        
        # Extract consignee
        print("\n" + "=" * 80)
        print("EXTRACTING CONSIGNEE:")
        print("=" * 80)
        consignee = extract_consignee(ocr_text)
        
        result_text = f"\nExtracted Consignee: '{consignee}'\n"
        print(result_text)
        
        # Write to file with UTF-8
        with open("pallipattu_result.txt", "w", encoding="utf-8") as f:
            f.write(f"OCR TEXT:\n{ocr_text}\n\n")
            f.write("=" * 80 + "\n")
            f.write(result_text)
            
            # Check if it has spaces
            if consignee:
                if "T R S" in consignee:
                    msg = "✓ Spaces preserved in 'T R S'"
                    print(msg)
                    f.write(msg + "\n")
                elif "TRS" in consignee:
                    msg = "✗ Spaces NOT preserved - got 'TRS' instead of 'T R S'"
                    print(msg)
                    f.write(msg + "\n")
        
        print("\n✓ Result saved to pallipattu_result.txt")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
