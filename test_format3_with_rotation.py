"""
Enhanced Format 3 Multi-Page Extractor with Rotation Correction
Handles skewed/tilted invoices like page 11
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageOps
import logging
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3

logging.basicConfig(level=logging.WARNING)

def rotate_image_if_needed(img):
    """
    Detect and correct image rotation using Tesseract OSD
    Handles skewed/tilted invoices
    """
    try:
        # Try to detect orientation
        osd = pytesseract.image_to_osd(img)
        
        # Parse rotation angle
        rotation = 0
        for line in osd.split('\n'):
            if 'Rotate:' in line:
                rotation = int(line.split(':')[1].strip())
                break
        
        # Rotate if needed
        if rotation != 0:
            # Tesseract returns degrees to rotate back to upright
            # 0 = no rotation, 90 = rotate 90° CCW, etc.
            img = img.rotate(360 - rotation, expand=True)
            print(f"      🔄 Rotated {rotation}° to correct orientation")
        
        return img
    except Exception as e:
        # If OSD fails, try basic preprocessing
        return img


def preprocess_for_ocr(img):
    """Enhanced preprocessing with rotation correction"""
    # Step 1: Rotate if needed
    img = rotate_image_if_needed(img)
    
    # Step 2: Convert to grayscale and enhance
    img = img.convert('L')
    img = ImageOps.autocontrast(img)
    
    return img


print("=" * 80)
print("FORMAT 3 MULTI-PAGE EXTRACTION (WITH ROTATION CORRECTION)")
print("PDF: DocScanner 23-Dec-2025 05-02 PM.pdf")
print("Expected: 20 pages, 11 invoices")
print("=" * 80)

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"

print("\n📄 Converting PDF to images...")
try:
    pages = convert_from_path(pdf_path, dpi=200)
    print(f"✅ Converted {len(pages)} pages")
except Exception as e:
    print(f"❌ Error converting PDF: {e}")
    sys.exit(1)

print("\n🔍 Processing all pages with rotation correction...")
print("-" * 80)

invoices = []
current_invoice = None

for page_num, page in enumerate(pages, 1):
    print(f"\n📄 Page {page_num}/{len(pages)}")
    
    # Apply preprocessing with rotation correction
    try:
        page_preprocessed = preprocess_for_ocr(page)
        text = pytesseract.image_to_string(page_preprocessed, lang='eng', config='--psm 6')
    except Exception as e:
        print(f"   ❌ OCR failed: {e}")
        continue
    
    # Check if this page has invoice data
    if 'INVOICE' in text.upper() and 'DATE' in text.upper():
        invoice_date = extract_invoice_date_format3(text)
        branch = extract_branch_refined(text)
        
        if invoice_date or branch:
            invoice_data = {
                'page': page_num,
                'date': invoice_date or 'NOT FOUND',
                'branch': branch or 'NOT FOUND'
            }
            
            # Avoid duplicates
            if not current_invoice or (current_invoice['date'] != invoice_data['date']):
                invoices.append(invoice_data)
                current_invoice = invoice_data
                
                print(f"   ✅ Found Invoice #{len(invoices)}")
                print(f"      Date: {invoice_data['date']}")
                print(f"      Branch: {invoice_data['branch']}")
            else:
                print(f"   ℹ️  Continuation of Invoice #{len(invoices)}")
        else:
            print(f"   ℹ️  Contains invoice text but data not extracted")
    else:
        print(f"   ℹ️  No invoice markers found")

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)

print(f"\n📊 Total Invoices Found: {len(invoices)}")
print(f"📄 Total Pages Processed: {len(pages)}")
print(f"🎯 Expected Invoices: 11")
print(f"{'✅ SUCCESS!' if len(invoices) == 11 else '⚠️  Missing: ' + str(11 - len(invoices))}")

if len(invoices) > 0:
    print("\n📋 Extracted Invoice Data:")
    print("-" * 80)
    print(f"{'#':<4} {'Page':<6} {'Date':<15} {'Branch':<20}")
    print("-" * 80)
    
    for i, inv in enumerate(invoices, 1):
        print(f"{i:<4} {inv['page']:<6} {inv['date']:<15} {inv['branch']:<20}")
    
    print("-" * 80)
    
    dates_found = sum(1 for inv in invoices if inv['date'] != 'NOT FOUND')
    branches_found = sum(1 for inv in invoices if inv['branch'] != 'NOT FOUND')
    
    print(f"\n📈 Extraction Success Rate:")
    print(f"   Dates: {dates_found}/{len(invoices)} ({dates_found/len(invoices)*100:.0f}%)")
    print(f"   Branches: {branches_found}/{len(invoices)} ({branches_found/len(invoices)*100:.0f}%)")

# Save results
output_file = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_final_results.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Total Invoices: {len(invoices)}/11\n")
    f.write(f"Success Rate - Dates: {dates_found}/{len(invoices)}\n")
    f.write(f"Success Rate - Branches: {branches_found}/{len(invoices)}\n\n")
    for i, inv in enumerate(invoices, 1):
        f.write(f"{i}. Page {inv['page']}: {inv['date']} - {inv['branch']}\n")

print(f"\n💾 Results saved to: {output_file}")
print("=" * 80)
