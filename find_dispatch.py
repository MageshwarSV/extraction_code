# Fixed: Stop at newlines and filter unwanted text
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
import re
from difflib import SequenceMatcher

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\dispatch_final_results.txt"


def fuzzy_match(text1, text2, threshold=0.6):
    """Check if two strings are similar (handles OCR errors)"""
    ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    return ratio >= threshold


def extract_destination_robust(text):
    """
    Extract destination with robust OCR error handling.
    Handles multi-word destinations like "Perambur purasawalkam"
    Stops at newlines and filters common unwanted text.
    """
    
    # Find lines containing "Dispatch To"
    lines = text.split('\n')
    
    for line in lines:
        # Skip lines without "Dispatch To" pattern
        if not re.search(r'dispatch\s*to', line, re.IGNORECASE):
            continue
        
        # Extract destination from this line only
        # Pattern: "Dispatch To" followed by words until end of meaningful content
        match = re.search(r'Dispatch\s*To\s*[:\s]*([A-Za-z][A-Za-z\s\-]*)', line, re.IGNORECASE)
        if match:
            destination = match.group(1).strip()
            
            # Clean up: remove trailing noise
            # Remove common unwanted words
            stop_words = ['incoterms', 'for-door', 'delivery', 'shipment', 'dispatch', 
                          'from', 'invoice', 'date', 'no', 'number', 'consignee']
            words = destination.split()
            clean_words = []
            for w in words:
                # Stop if we hit a stop word
                if w.lower() in stop_words:
                    break
                # Stop if single char (noise like 'i', 'a')
                if len(w) == 1 and w.lower() not in ['a']:  # keep 'A' in names
                    continue
                clean_words.append(w)
            
            destination = ' '.join(clean_words).strip()
            
            # Remove trailing single letters (OCR noise)
            destination = re.sub(r'\s+[a-z]$', '', destination, flags=re.IGNORECASE)
            
            if len(destination) >= 3:
                return destination, "line_extract"
    
    # Fallback: Fuzzy matching for OCR errors
    words = text.split()
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^a-zA-Z0-9]', '', word)
        
        if len(clean_word) >= 5 and fuzzy_match(clean_word, "dispatch", 0.5):
            for j in range(i+1, min(i+4, len(words))):
                next_word = re.sub(r'[^a-zA-Z0-9]', '', words[j])
                if fuzzy_match(next_word, "to", 0.6) or next_word.lower() == "to":
                    dest_words = []
                    for k in range(j+1, min(j+5, len(words))):
                        w = words[k]
                        clean_w = re.sub(r'[^a-zA-Z\-]', '', w)
                        if not clean_w or len(clean_w) < 2:
                            break
                        if any(c.isdigit() for c in w):
                            break
                        if clean_w.lower() in ['dispatch', 'from', 'invoice', 'date', 'no', 
                                               'incoterms', 'for-door', 'delivery', 'shipment']:
                            break
                        dest_words.append(clean_w)
                    
                    if dest_words:
                        return ' '.join(dest_words), "fuzzy_match"
    
    return "NOT FOUND", "no_match"


# Test
print("=" * 70)
print("TESTING CLEAN EXTRACTION")
print("=" * 70)

test_cases = [
    "Dispatch From Salem Dispatch To Perambur purasawalkam\nIncoterms FOR-DOOR",
    "Dispatch To Soolagiri\nIncoterms FOR-DOOR DELIVERY",
    "Dispatch To Chennai a\nIncoterms",
]

for test in test_cases:
    dest, method = extract_destination_robust(test)
    print(f"Input:  {repr(test[:60])}")
    print(f"Result: '{dest}' ({method})")
    print()

# Run on PDF
print("\n" + "=" * 70)
print("PDF EXTRACTION - CLEAN DESTINATIONS")
print("=" * 70 + "\n")

pages = convert_from_path(pdf_path, dpi=300)
results = []

for page_num, page in enumerate(pages, 1):
    text = pytesseract.image_to_string(page, config='--psm 6', lang='eng')
    
    rotated = page.rotate(90, expand=True)
    rotated_text = pytesseract.image_to_string(rotated, config='--psm 6', lang='eng')
    
    if 'CONSIGNMENT' in rotated_text.upper() and 'NOTE' in rotated_text.upper():
        page_type = "CONSIGNMENT"
        destination = "-"
        method = "-"
    else:
        page_type = "INVOICE"
        destination, method = extract_destination_robust(text)
    
    results.append({
        "page": page_num,
        "type": page_type,
        "destination": destination,
        "method": method
    })
    
    print(f"Page {page_num:2d}: {page_type:12s} | {destination:28s}")

# Save results
with open(output_file, 'w') as f:
    f.write("=" * 70 + "\n")
    f.write("DISPATCH EXTRACTION - FINAL CLEAN RESULTS\n")
    f.write("=" * 70 + "\n\n")
    
    f.write(f"{'Page':<6} {'Type':<14} {'Destination'}\n")
    f.write("-" * 50 + "\n")
    
    for r in results:
        f.write(f"{r['page']:<6} {r['type']:<14} {r['destination']}\n")
    
    invoice_pages = [r for r in results if r['type'] == 'INVOICE']
    found = [r for r in invoice_pages if r['destination'] != 'NOT FOUND']
    
    f.write("\n" + "=" * 70 + "\n")
    f.write("SUMMARY\n")
    f.write("=" * 70 + "\n")
    f.write(f"Destinations Found: {len(found)}/{len(invoice_pages)} invoice pages\n\n")
    
    for r in found:
        f.write(f"  Page {r['page']:2d}: {r['destination']}\n")

print(f"\n\nResults saved to: {output_file}")
