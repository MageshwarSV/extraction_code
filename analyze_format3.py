import pytesseract
from PIL import Image, ImageEnhance, ImageOps
import sys

def analyze_format3_doc():
    """Comprehensive analysis of Format 3 document"""
    img_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_page_1.png"
    
    print("=" * 80)
    print("FORMAT 3 DOCUMENT ANALYSIS - JEW CEMENT LIMITED")
    print("=" * 80)
    
    # Load and preprocess image
    img = Image.open(img_path)
    print(f"\nOriginal Image Size: {img.size}")
    
    # Convert to grayscale and enhance
    img_gray = img.convert('L')
    img_enhanced = ImageOps.autocontrast(img_gray)
    
    # Try multiple PSM modes for best results
    configs = [
        '--psm 6',  # Assume uniform block of text
        '--psm 4',  # Assume single column of text
        '--psm 3',  # Fully automatic page segmentation
    ]
    
    all_text = []
    for config in configs:
        try:
            text = pytesseract.image_to_string(img_enhanced, lang='eng', config=config)
            if text and len(text.strip()) > len(''.join(all_text)):
                all_text = [text]
        except Exception as e:
            print(f"Config {config} failed: {e}")
    
    final_text = all_text[0] if all_text else ""
    
    print("\n" + "=" * 80)
    print("FULL EXTRACTED TEXT")
    print("=" * 80 + "\n")
    print(final_text)
    
    print("\n" + "=" * 80)
    print("DOCUMENT STRUCTURE ANALYSIS")
    print("=" * 80)
    
    lines = final_text.split('\n')
    print(f"\nTotal Lines: {len(lines)}")
    print(f"Total Characters: {len(final_text)}")
    
    # Identify key sections
    print("\n--- IDENTIFIABLE SECTIONS ---")
    keywords = ['TAX INVOICE', 'Invoice', 'Date', 'Bill', 'Consignee', 'Vehicle', 
                'Quantity', 'Rate', 'Amount', 'GST', 'Total', 'GSTIN', 'E-Way', 
                'Driver', 'Mobile', 'Destination', 'LR', 'RR']
    
    for keyword in keywords:
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                print(f"  Line {i+1}: {keyword} → {line.strip()[:80]}")
                break
    
    print("\n" + "=" * 80)
    
    # Save to file for review
    with open(r'c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_ocr_text.txt', 'w', encoding='utf-8') as f:
        f.write(final_text)
    print("Full OCR text saved to: format3_ocr_text.txt")

if __name__ == "__main__":
    analyze_format3_doc()
