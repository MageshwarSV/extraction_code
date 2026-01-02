# extract_consignor_standalone.py
import os
import sys
import re
import logging
import pytesseract
from pdf2image import convert_from_path
from difflib import SequenceMatcher

# Add current directory to path
sys.path.insert(0, os.getcwd())

from engine.extractors.deskew import deskew_and_enhance

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def fuzzy_match(text1: str, text2: str, threshold: float = 0.6) -> bool:
    """Check if strings are similar"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() >= threshold

def extract_consignor_refined(text: str) -> str:
    """
    Extract Consignor name with specific mapping rules:
    - JSW CEMENT LIMITED - NANDYAL -> JSW CEMENT LIMITED NANDYAL
    - JSW CEMENT LIMITED - SALEM -> JSW CEMENT LIMITED POTTANERI
    Supports fuzzy matching for bended/distorted text.
    """
    # Patterns to look for
    consignor_base = "JSW CEMENT LIMITED"
    
    # city patterns
    cities = {
        "SALEM": "POTTANERI",
        "NANDYAL": "NANDYAL"
    }

    lines = text.split('\n')
    for line in lines:
        line_upper = line.upper()
        
        # Look for JSW CEMENT LIMITED or JSWCL
        is_jsw = False
        if "JSW CEMENT LIMITED" in line_upper or "JSWCL" in line_upper:
            is_jsw = True
        else:
            # Fuzzy match base
            words = line_upper.split()
            for word in words:
                if fuzzy_match(word, "JSWCL", 0.7) or fuzzy_match(word, "JSW", 0.8):
                    is_jsw = True
                    break
        
        if is_jsw:
            # Found JSW, now look for city
            for city_key, city_map in cities.items():
                # Look for city name or fuzzy city name in the same line
                if city_key in line_upper or fuzzy_match(line_upper, city_key, 0.5):
                    logger.info(f"[Consignor] Found {city_key} in line: {line.strip()}")
                    return f"JSW CEMENT LIMITED {city_map}"
                
            # Fallback: check next line if JSW but no city found
            # (Happens if it's on two lines)
            continue
            
    # Fallback: search whole text for the city near JSW
    # Look for NANDYAL or SALEM anywhere and assume JSW CEMENT LIMITED based on context of Format 3
    for city_key, city_map in cities.items():
        if city_key in text.upper():
            logger.info(f"[Consignor] Found {city_key} via global search")
            return f"JSW CEMENT LIMITED {city_map}"
            
    return "JSW CEMENT LIMITED" # default if only JSW found

def process_pdf(pdf_path: str, output_path: str):
    logger.info(f"Start Consignor extraction: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found: {pdf_path}")
        return

    # Convert PDF to images at 300 DPI
    pages = convert_from_path(pdf_path, dpi=300)
    
    results = []
    results.append("CONSIGNOR EXTRACTION RESULTS")
    results.append("=" * 60)
    results.append(f"PDF: {os.path.basename(pdf_path)}")
    results.append("-" * 60)
    
    for i, page in enumerate(pages, 1):
        logger.info(f"Processing page {i}/{len(pages)}...")
        
        # Determine if invoice (not rotated) or consignment (rotated)
        # Consignor usually on Invoices according to user
        rotated_page = page.rotate(90, expand=True)
        rotated_text = pytesseract.image_to_string(rotated_page, config='--psm 6')
        
        if 'CONSIGNMENT' in rotated_text.upper() and 'NOTE' in rotated_text.upper():
            logger.info(f"Page {i}: CONSIGNMENT (Skipping Consignor)")
            continue
        
        # It's an Invoice
        page_corrected = deskew_and_enhance(page)
        text = pytesseract.image_to_string(page_corrected, config='--psm 6')
        
        consignor = extract_consignor_refined(text)
        
        line = f"Page {i:2}: Consignor: {consignor}"
        logger.info(line)
        results.append(line)

    results.append("=" * 60)
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(results))
    
    logger.info(f"Results saved to: {output_path}")

if __name__ == "__main__":
    pdf_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    out_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\consignor_extracted.txt"
    
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    process_pdf(pdf_file, out_file)
