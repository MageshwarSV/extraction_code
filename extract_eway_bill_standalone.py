# extract_eway_bill_standalone.py
import os
import sys
import re
import logging
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Add current directory to path
sys.path.insert(0, os.getcwd())

from engine.extractors.deskew import deskew_and_enhance

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def extract_eway_bill_refined(text: str) -> str:
    """
    Extract 12-digit E-Way Bill number from OCR text.
    Handles label variations and noise.
    """
    # 1. Look for E-Way label with fuzzy variations
    # Patterns for labels: E-Way No, E-Way Bill No, E-Way No/Validity, etc.
    label_patterns = [
        r'E-Way\s*No',
        r'E-Way\s*Bill\s*No',
        r'E-Way\s*No/Validity',
        r'E-WayNo',
        r'E\s*Way\s*Bill',
        r'E-Wway\s*No', # OCR error variation
        r'E-Way\s*Ne',   # OCR error variation
        r'Validity'
    ]
    
    # Combined regex for label + potential characters + 12 digits
    # The [^0-9]* handles any noise characters like :, -, /, ", etc.
    for pattern in label_patterns:
        # Look for 12 digits after the label
        # Allowing some noise characters between label and digits
        regex = rf'({pattern})[^0-9\n]*(\d{{12}})'
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            eway_no = match.group(2)
            logger.info(f"[E-Way] Found with label '{match.group(1)}': {eway_no}")
            return eway_no

    # 2. Fallback: Search for any 12-digit number that matches E-Way bill format
    # E-Way bills in India usually start with 1-9 (often 56... or similar recently)
    all_12_digits = re.findall(r'\b\d{12}\b', text)
    if all_12_digits:
        # Filter out common false positives if necessary (none obvious for now)
        logger.info(f"[E-Way] Found 12-digit sequence as fallback: {all_12_digits[0]}")
        return all_12_digits[0]
    
    # 3. Last Fallback: Even if digits are broken or mixed with letters (e.g. O instead of 0)
    # Search for labels then clean up next 14 characters
    for pattern in label_patterns:
        match = re.search(rf'({pattern})(.{{1,20}})', text, re.IGNORECASE)
        if match:
            potential_num = match.group(2)
            # Normalize common OCR errors in digits
            normalized = (potential_num
                          .replace('O', '0')
                          .replace('o', '0')
                          .replace('I', '1')
                          .replace('l', '1')
                          .replace('S', '5')
                          .replace('s', '5')
                          .replace('B', '8')
                          .replace('G', '6'))
            # Find first 12-digit block in normalized
            digit_match = re.search(r'(\d{12})', normalized)
            if digit_match:
                logger.info(f"[E-Way] Found after normalization: {digit_match.group(1)}")
                return digit_match.group(1)
                
    return ""

def process_pdf(pdf_path: str, output_path: str):
    logger.info(f"Start E-Way Bill extraction: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found: {pdf_path}")
        return

    # Convert PDF to images at 300 DPI for high quality
    pages = convert_from_path(pdf_path, dpi=300)
    
    results = []
    results.append("E-WAY BILL EXTRACTION RESULTS")
    results.append("=" * 60)
    results.append(f"PDF: {os.path.basename(pdf_path)}")
    results.append("-" * 60)
    
    for i, page in enumerate(pages, 1):
        logger.info(f"Processing page {i}/{len(pages)}...")
        
        # Determine if invoice (not rotated) or consignment (rotated)
        # We only care about Invoices for E-Way Bills
        # Rotated check
        rotated_page = page.rotate(90, expand=True)
        rotated_text = pytesseract.image_to_string(rotated_page, config='--psm 6')
        
        if 'CONSIGNMENT' in rotated_text.upper() and 'NOTE' in rotated_text.upper():
            logger.info(f"Page {i}: CONSIGNMENT (Skipping E-Way)")
            continue
        
        # It's an Invoice
        # Apply deskew and enhance
        page_corrected = deskew_and_enhance(page)
        
        # Full text OCR with PSM 1 (Automatic orientation) or PSM 3
        text = pytesseract.image_to_string(page_corrected, config='--psm 3')
        
        eway_bill = extract_eway_bill_refined(text)
        
        if eway_bill:
            line = f"Page {i:2}: E-Way Bill: {eway_bill}"
            logger.info(line)
            results.append(line)
        else:
            logger.warning(f"Page {i:2}: E-Way Bill: NOT FOUND")
            results.append(f"Page {i:2}: E-Way Bill: NOT FOUND")

    results.append("=" * 60)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(results))
    
    logger.info(f"Results saved to: {output_path}")

if __name__ == "__main__":
    pdf_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    out_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\eway_bill_extracted.txt"
    
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    process_pdf(pdf_file, out_file)
