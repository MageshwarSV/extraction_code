"""
Multi-Page Invoice Extraction Test for Format 3
Tests branch and date extraction across all 11 invoices in 20-page PDF
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import logging
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3

logging.basicConfig(level=logging.WARNING)

print("=" * 80)
print("FORMAT 3 MULTI-PAGE EXTRACTION TEST")
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

print("\n🔍 Processing all pages and extracting data...")
print("-" * 80)

# Track discovered invoices
invoices = []
current_invoice = None

for page_num, page in enumerate(pages, 1):
    print(f"\n📄 Page {page_num}/{len(pages)}")
    
    # Extract text from page WITH DESKEWING (perspective correction disabled for now)
    try:
        # Import deskew function
        from engine.extractors.deskew import deskew_and_enhance
        
        # Apply deskew preprocessing
        page_corrected = deskew_and_enhance(page)
        
        # Run OCR on corrected image
        text = pytesseract.image_to_string(page_corrected, lang='eng', config='--psm 6')
    except Exception as e:
        print(f"   ❌ OCR failed: {e}")
        continue
    
    # Check if this page has "Invoice Date/Time" (indicates new invoice)
    if 'INVOICE' in text.upper() and 'DATE' in text.upper():
        # Try to extract invoice data
        from engine.extractors.invoice_datetime_full import extract_invoice_datetime_full
        
        invoice_date = extract_invoice_date_format3(text)  # For display
        invoice_datetime_full = extract_invoice_datetime_full(text)  # For deduplication
        branch = extract_branch_refined(text)
        
        if invoice_date or branch:
            # Found a new invoice
            invoice_data = {
                'page': page_num,
                'date': invoice_date or 'NOT FOUND',
                'datetime_full': invoice_datetime_full,  # Use for deduplication
                'branch': branch or 'NOT FOUND'
            }
            
            # Check if this is different from previous invoice
            # Compare FULL datetime (with time) OR branch to avoid false duplicates
            is_duplicate = False
            if current_invoice:
                # Same invoice if BOTH datetime AND branch match
                if (current_invoice.get('datetime_full') == invoice_data['datetime_full'] and 
                    current_invoice['branch'] == invoice_data['branch']):
                    is_duplicate = True
            
            if not is_duplicate:
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
print("EXTRACTION SUMMARY")
print("=" * 80)

print(f"\n📊 Total Invoices Found: {len(invoices)}")
print(f"📄 Total Pages Processed: {len(pages)}")
print(f"✅ Expected Invoices: 11")

if len(invoices) > 0:
    print("\n📋 Extracted Invoice Data:")
    print("-" * 80)
    print(f"{'#':<4} {'Page':<6} {'Date':<15} {'Branch':<20}")
    print("-" * 80)
    
    for i, inv in enumerate(invoices, 1):
        print(f"{i:<4} {inv['page']:<6} {inv['date']:<15} {inv['branch']:<20}")
    
    print("-" * 80)
    
    # Statistics
    dates_found = sum(1 for inv in invoices if inv['date'] != 'NOT FOUND')
    branches_found = sum(1 for inv in invoices if inv['branch'] != 'NOT FOUND')
    
    print(f"\n📈 Extraction Success Rate:")
    print(f"   Dates: {dates_found}/{len(invoices)} ({dates_found/len(invoices)*100:.0f}%)")
    print(f"   Branches: {branches_found}/{len(invoices)} ({branches_found/len(invoices)*100:.0f}%)")

else:
    print("\n❌ No invoices found!")

print("\n" + "=" * 80)
print("👉 USER: Please verify if the count and data are correct!")
print("=" * 80)

# Save results to file for review
output_file = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_extraction_results.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("FORMAT 3 MULTI-PAGE EXTRACTION RESULTS\n")
    f.write("=" * 80 + "\n")
    f.write(f"Total Pages: {len(pages)}\n")
    f.write(f"Total Invoices Found: {len(invoices)}\n")
    f.write(f"Expected Invoices: 11\n\n")
    
    if len(invoices) > 0:
        f.write("Invoice Details:\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'#':<4} {'Page':<6} {'Date':<15} {'Branch':<20}\n")
        f.write("-" * 80 + "\n")
        for i, inv in enumerate(invoices, 1):
            f.write(f"{i:<4} {inv['page']:<6} {inv['date']:<15} {inv['branch']:<20}\n")
        
        dates_found = sum(1 for inv in invoices if inv['date'] != 'NOT FOUND')
        branches_found = sum(1 for inv in invoices if inv['branch'] != 'NOT FOUND')
        f.write("\n" + "-" * 80 + "\n")
        f.write(f"Success Rate:\n")
        f.write(f"  Dates: {dates_found}/{len(invoices)} ({dates_found/len(invoices)*100:.0f}%)\n")
        f.write(f"  Branches: {branches_found}/{len(invoices)} ({branches_found/len(invoices)*100:.0f}%)\n")

print(f"\n💾 Full results saved to: {output_file}")
