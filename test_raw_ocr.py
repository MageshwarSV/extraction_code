"""
Check Raw OCR Output - See what Tesseract actually extracts
"""
import pytesseract
from pdf2image import convert_from_path

PDF_PATH = r"C:\Users\avin4\Desktop\hipdf\vechile.pdf"
pytesseract.pytesseract.tesseract_cmd = r"C:\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-25.07.0\Library\bin"

print("="*60)
print("RAW OCR OUTPUT - What Tesseract sees")
print("="*60)

# Convert PDF to image
pages = convert_from_path(PDF_PATH, dpi=300, poppler_path=POPPLER_PATH)

for i, page in enumerate(pages):
    print(f"\n--- PAGE {i+1} ---")
    
    # Get raw OCR text
    text = pytesseract.image_to_string(page, lang='eng')
    
    # Find vehicle number in text
    print("\nFull OCR Text:")
    print(text)
    
    print("\n" + "="*60)
    print("SEARCHING FOR VEHICLE NUMBER...")
    print("="*60)
    
    # Look for lines with "Vehicle" or similar
    for line in text.split('\n'):
        if any(word in line.upper() for word in ['VEHICLE', 'WAGON', 'TN', 'NO']):
            print(f"  {line}")
    
    print("\n" + "="*60)
