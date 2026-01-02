"""
Format 3 Complete Extraction - All Fields (Tesseract)
Extracts: Branch, Invoice Date, GC Number from all 20 pages
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.branch_extractor import extract_branch_refined
from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
from engine.extractors.gc_number_extractor import extract_gc_number_from_pdf_page
from engine.extractors.deskew import deskew_and_enhance
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.WARNING)

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_file = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_extraction_log.txt"

print("=" * 80)
print("FORMAT 3 COMPLETE EXTRACTION")
print("=" * 80)
print(f"PDF: DocScanner 23-Dec-2025 05-02 PM.pdf")
print(f"Extracting: Branch, Invoice Date, GC Number")
print(f"Output: format3_extraction_log.txt")
print("=" * 80)

# Convert PDF
print("\n📄 Converting PDF to images...")
pages = convert_from_path(pdf_path, dpi=200)
print(f"✅ Converted {len(pages)} pages\n")

# Process each page
results = []
gc_numbers_by_page = {}  # Store GC numbers with their page numbers

for page_num, page in enumerate(pages, 1):
    print(f"Processing Page {page_num}/{len(pages)}...", end=" ")
    
    # Apply deskew preprocessing
    page_preprocessed = deskew_and_enhance(page)
    
    # Run OCR
    text = pytesseract.image_to_string(page_preprocessed, config='--psm 6')
    
    # Extract fields
    branch = extract_branch_refined(text)
    invoice_date = extract_invoice_date_format3(text)
    gc_number = extract_gc_number_from_pdf_page(page)
    
    # Store GC number if found
    if gc_number:
        gc_numbers_by_page[page_num] = gc_number
    
    # Check if invoice page (has date or branch)
    is_invoice = bool(branch or invoice_date)
    
    result = {
        'page': page_num,
        'is_invoice': is_invoice,
        'branch': branch or '-',
        'date': invoice_date or '-',
        'gc_number': '-'  # Will be filled in next step
    }
    
    results.append(result)
    
    status = "✅" if is_invoice else "⏭️"
    print(f"{status}")

# Post-process: Associate GC numbers with nearest invoice page
print("\n🔗 Associating GC numbers with invoices...")
for page_num, gc_num in gc_numbers_by_page.items():
    # Find nearest invoice page (search +/- 2 pages)
    nearest_invoice = None
    min_distance = 999
    
    for result in results:
        if result['is_invoice']:
            distance = abs(result['page'] - page_num)
            if distance < min_distance and distance <= 2:
                min_distance = distance
                nearest_invoice = result
    
    if nearest_invoice:
        nearest_invoice['gc_number'] = gc_num
        print(f"  Page {page_num} GC ({gc_num}) → Invoice Page {nearest_invoice['page']}")
    else:
        print(f"  Page {page_num} GC ({gc_num}) → No nearby invoice found")

# Write to log file
print(f"\n📝 Writing results to {output_file}...")

with open(output_file, 'w', encoding='utf-8') as f:
    # Header
    f.write("=" * 80 + "\n")
    f.write("FORMAT 3 EXTRACTION LOG\n")
    f.write("=" * 80 + "\n")
    f.write(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"PDF: DocScanner 23-Dec-2025 05-02 PM.pdf\n")
    f.write(f"Total Pages: {len(pages)}\n")
    f.write("Fields Extracted: Branch, Invoice Date, GC Number\n")
    f.write("=" * 80 + "\n\n")
    
    # Summary
    invoice_pages = [r for r in results if r['is_invoice']]
    f.write(f"SUMMARY:\n")
    f.write(f"  Invoice Pages: {len(invoice_pages)}/{len(pages)}\n")
    f.write(f"  Branch Found: {sum(1 for r in invoice_pages if r['branch'] != '-')}/{len(invoice_pages)}\n")
    f.write(f"  Date Found: {sum(1 for r in invoice_pages if r['date'] != '-')}/{len(invoice_pages)}\n")
    f.write(f"  GC Number Found: {sum(1 for r in invoice_pages if r['gc_number'] != '-')}/{len(invoice_pages)}\n")
    f.write("\n" + "=" * 80 + "\n\n")
    
    # Detailed results
    f.write("DETAILED EXTRACTION RESULTS:\n")
    f.write("=" * 80 + "\n")
    f.write(f"{'Page':<6} {'Type':<10} {'Branch':<20} {'Date':<15} {'GC Number':<10}\n")
    f.write("-" * 80 + "\n")
    
    for r in results:
        page_type = "INVOICE" if r['is_invoice'] else "OTHER"
        f.write(f"{r['page']:<6} {page_type:<10} {r['branch']:<20} {r['date']:<15} {r['gc_number']:<10}\n")
    
    f.write("=" * 80 + "\n\n")
    
    # Invoice-only table
    f.write("INVOICE PAGES ONLY:\n")
    f.write("=" * 80 + "\n")
    f.write(f"{'#':<4} {'Page':<6} {'Branch':<20} {'Date':<15} {'GC Number':<10}\n")
    f.write("-" * 80 + "\n")
    
    for idx, r in enumerate(invoice_pages, 1):
        f.write(f"{idx:<4} {r['page']:<6} {r['branch']:<20} {r['date']:<15} {r['gc_number']:<10}\n")
    
    f.write("=" * 80 + "\n")

print("✅ Complete!\n")

# Display summary
print("=" * 80)
print("EXTRACTION SUMMARY")
print("=" * 80)
print(f"Invoice Pages Found: {len(invoice_pages)}/{len(pages)}")
if len(invoice_pages) > 0:
    print(f"Branch Extraction: {sum(1 for r in invoice_pages if r['branch'] != '-')}/{len(invoice_pages)} ({sum(1 for r in invoice_pages if r['branch'] != '-')/len(invoice_pages)*100:.0f}%)")
    print(f"Date Extraction: {sum(1 for r in invoice_pages if r['date'] != '-')}/{len(invoice_pages)} ({sum(1 for r in invoice_pages if r['date'] != '-')/len(invoice_pages)*100:.0f}%)")
    print(f"GC Number Extraction: {sum(1 for r in invoice_pages if r['gc_number'] != '-')}/{len(invoice_pages)} ({sum(1 for r in invoice_pages if r['gc_number'] != '-')/len(invoice_pages)*100:.0f}%)")
else:
    print("No invoice pages found!")
print("=" * 80)
print(f"\n✅ Results saved to: format3_extraction_log.txt")
print("=" * 80)
