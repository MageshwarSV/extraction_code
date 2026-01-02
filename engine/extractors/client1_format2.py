# engine/extractors/client1_format2.py
# -------------------------------------------------------------
# Client 1 - Format 2 OCR Extractor
# Extracts data from Jindal Industries Format 2 invoices
# Uses Format 2-specific field labels (Ship To, Dated, etc.)
# -------------------------------------------------------------

import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

# Import shared utilities from Format 1 (helpers only, not run())
import sys
import importlib.util

# Load Format 1 module to access helper functions
spec = importlib.util.spec_from_file_location(
    "client1_format1",
    os.path.join(os.path.dirname(__file__), "client1_format1.py")
)
fmt1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmt1)

# -------------------------
# Logging
# -------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.DEBUG if os.getenv("EXTRACTOR_DEBUG") else logging.INFO)

# -------------------------
# Format 2 Specific Extractors
# -------------------------

def extract_invoice_no_format2(text: str) -> Optional[str]:
    """Extract Invoice No from Format 2: 'Invoice No : CN25000862'"""
    patterns = [
        r'Invoice\s*No\s*[:.-]\s*([A-Z]{2}\d{7,10})',
        r'Invoice\s*No\s*[:.-]?\s*([A-Z0-9]{8,15})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_invoice_date_format2(text: str) -> Optional[str]:
    """Extract Invoice Date from Format 2: 'Dated: 07.11.2025'"""
    patterns = [
        r'Dated\s*[:.-]\s*(\d{2}\.\d{2}\.\d{4})',
        r'Dated\s*[:.-]\s*(\d{2}[./-]\d{2}[./-]\d{4})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            # Normalize using Format 1's helper
            parsed = fmt1.try_parse_date(date_str)
            if parsed:
                return parsed.strftime("%d.%m.%Y")
    return None


def extract_ewb_no_format2(text: str) -> Optional[str]:
    """Extract E-Way Bill No from Format 2: 'EWB No:'"""
    patterns = [
        r'EWB\s*No\s*[:.-]\s*(\d{12})',
        r'E-?Way\s*Bill\s*No\s*[:.-]\s*(\d{12})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_ewb_date_format2(text: str) -> Optional[str]:
    """Extract E-Way Bill Date from Format 2: 'EWB Date:' (separate field in Format 2)"""
    patterns = [
        r'EWB\s*Date\s*[:.-]\s*(\d{2}\.\d{2}\.\d{4})',
        r'E-?Way\s*Bill\s*Date\s*[:.-]\s*(\d{2}[./-]\d{2}[./-]\d{4})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            parsed = fmt1.try_parse_date(date_str)
            if parsed:
                return parsed.strftime("%d.%m.%Y")
    return None


def extract_ship_to_format2(text: str) -> Optional[str]:
    """
    Extract company name from 'Ship To:' section (Format 2's version of Consignee)
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'Ship\s*To\s*[:.-]', line, re.IGNORECASE):
            # Found "Ship To:" label, extract company name from next lines
            for j in range(i, min(i + 5, len(lines))):
                cand = lines[j].strip()
                # Skip the label line itself
                if re.search(r'Ship\s*To', cand, re.IGNORECASE):
                    continue
                # Skip lines with GST, address keywords
                if re.search(r'(GST|State|Place|PIN|Floor|Road)', cand, re.IGNORECASE):
                    break
                # Check if this looks like a company name
                if cand and len(cand) > 3:
                    # Clean using Format 1's helper
                    cleaned = fmt1.clean_consignee(cand)
                    if cleaned:
                        logger.info(f"[Format2] Ship To (Consignee): {cleaned}")
                        return cleaned
    return None


def extract_vehicle_no_format2(text: str) -> Optional[str]:
    """Extract Vehicle No from Format 2: 'Vehicle No: KA05MS4111'"""
    patterns = [
        r'Vehicle\s*No\s*[:.-]\s*([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4})',
        r'Vehicle\s*No\s*[:.-]\s*([A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{3,4})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            veh = m.group(1).replace(' ', '')
            return veh.upper()
    return None


def extract_quantity_format2(text: str) -> Optional[str]:
    """
    Extract total quantity from TOTAL row in table
    Format 2 shows: TOTAL | 15.419 | (in MT)
    The quantity appears in the TOTAL row, last bold value
    """
    # Strategy 1: Look for TOTAL row pattern
    patterns = [
        r'TOTAL.*?(\d+\.\d{3})',  # TOTAL followed by decimal number (3 decimal places)
        r'TOTAL\s+(\d+\.\d+)',     # TOTAL followed by any decimal number
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            qty = m.group(1)
            logger.info(f"[Format2] Quantity from TOTAL row: {qty}")
            return qty
    
    # Strategy 2: Look for pattern in table structure
    # Sometimes OCR gives: "15.419" on separate line after items
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'TOTAL' in line.upper():
            # Check this line and next few lines for quantity
            search_lines = lines[i:min(i+3, len(lines))]
            for sl in search_lines:
                # Look for decimal number with 3+ decimal places
                m = re.search(r'(\d+\.\d{3})', sl)
                if m:
                    qty = m.group(1)
                    logger.info(f"[Format2] Quantity from TOTAL vicinity: {qty}")
                    return qty
    
    return None


# -------------------------
# Main Extraction Function
# -------------------------

def run(
    pdf_path: str,
    *,
    tesseract_cmd: Optional[str] = None,
    poppler_path: Optional[str] = None,
    save_raw_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format 2 Extraction - Extract from Jindal Industries Format 2 invoices
    
    Format 2 uses different field labels:
    - "Ship To:" instead of "Consignee:"
    - "Dated:" instead of "Invoice Date:"
    - "EWB No:" and "EWB Date:" as separate fields
    - Total quantity in table TOTAL row
    
    Returns same output structure as Format 1 for compatibility.
    """
    
    logger.info("=" * 80)
    logger.info("CLIENT 1 FORMAT 2 EXTRACTOR")
    logger.info("=" * 80)
    logger.info("Format: Jindal Industries Format 2")
    logger.info("PDF: %s", pdf_path)
    logger.info("=" * 80)
    
    # STEP 1: Run OCR using Format 1's infrastructure
    logger.info("\n📄 Running Tesseract OCR...")
    
    # Detect Tesseract and Poppler
    tess = fmt1._detect_tesseract(tesseract_cmd)
    logger.info("✓ Using Tesseract: %s", tess)
    
    poppler = fmt1._detect_poppler(poppler_path)
    if poppler:
        logger.info("✓ Using Poppler: %s", poppler)
    
    # Convert PDF to images and run OCR
    try:
        from pdf2image import convert_from_path
        if poppler:
            pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler)
        else:
            pages = convert_from_path(pdf_path, dpi=300)
        logger.info("✓ Rendered %d page(s) from PDF", len(pages))
    except Exception as e:
        raise RuntimeError(f"Failed to render PDF: {e}")
    
    # Run OCR on all pages using Format 1's preprocessing
    all_blocks: List[str] = []
    originals: List[Image.Image] = []
    
    for pg_num, pg in enumerate(pages, 1):
        logger.info("  Processing page %d...", pg_num)
        originals.append(pg)
        
        variants = fmt1._preprocess_variants_fast(pg)
        page_texts: List[str] = []
        
        for v in variants:
            page_texts.extend(fmt1._ocr_configs_fast(v))
        
        merged = fmt1._merge_text(page_texts) if page_texts else ""
        all_blocks.append(merged)
    
    # Combine all page text
    text = "\n".join(all_blocks)
    logger.info("✓ OCR completed. Total text length: %d characters", len(text))
    
    # STEP 2: Extract fields using Format 2 patterns
    logger.info("\n🔍 Extracting fields using Format 2 patterns...")
    
    invoice_no = extract_invoice_no_format2(text)
    logger.info("  Invoice No: %s", invoice_no or "NOT FOUND")
    
    invoice_date = extract_invoice_date_format2(text)
    logger.info("  Invoice Date (Dated): %s", invoice_date or "NOT FOUND")
    
    eway_no = extract_ewb_no_format2(text)
    logger.info("  E-Way Bill No: %s", eway_no or "NOT FOUND")
    
    eway_date = extract_ewb_date_format2(text)
    if not eway_date:
        eway_date = invoice_date  # Fallback to invoice date
    logger.info("  E-Way Bill Date: %s", eway_date or "NOT FOUND")
    
    consignee = extract_ship_to_format2(text)
    logger.info("  Consignee (Ship To): %s", consignee or "NOT FOUND")
    
    vehicle = extract_vehicle_no_format2(text)
    logger.info("  Vehicle No: %s", vehicle or "NOT FOUND")
    
    quantity = extract_quantity_format2(text)
    logger.info("  Quantity (TOTAL): %s MT", quantity or "NOT FOUND")
    
    # STEP 3: Reuse Format 1 extractors for common fields
    logger.info("\n🔄 Extracting remaining fields using Format 1 helpers...")
    
    # These fields have same labels in both formats
    lr_no = fmt1.extract_lr(text)
    logger.info("  L.R. No: %s", lr_no or "NOT FOUND")
    
    driver_mobile = fmt1.extract_driver_mobile(text)
    logger.info("  Driver Mobile: %s", driver_mobile or "NOT FOUND")
    
    rate = fmt1.extract_rate(text)
    logger.info("  Rate: %s", rate or "NOT FOUND")
    
    # Content name from HSN code
    content_name, _ = fmt1.extract_material_code_global(text)
    if not content_name:
        content_name = "PPC"  # Default
    logger.info("  Content Name: %s", content_name)
    
    # Goods type
    goods_type = "BAG" if re.search(r'\b(?:BAGS?|LOOSE)\b', text, re.IGNORECASE) else (
        "BULK" if re.search(r'\bBULK\b', text, re.IGNORECASE) else None
    )
    logger.info("  Goods Type: %s", goods_type or "NOT DETECTED")
    
    # Destination
    destination = fmt1.extract_destination(text)
    destination = fmt1.clean_destination(destination)
    logger.info("  Destination: %s", destination or "NOT FOUND")
    
    # Source
    despatch_city, city_count = fmt1.extract_despatch_city(text)
    logger.info("  Source: %s", despatch_city or "NOT FOUND")
    
    # IRN
    irn = fmt1.extract_irn(text)
    logger.info("  IRN: %s", irn or "NOT FOUND")
    
    # Consignor (always UltraTech/Jindal)
    consignor = "Jindal Industries Pvt Ltd"
    logger.info("  Consignor: %s", consignor)
    
    # STEP 4: Build output dictionary
    raw_data: Dict[str, Any] = {
        "Consignment No": lr_no,
        "Source": despatch_city,
        "Destination": destination,
        "E-Way Bill No": eway_no,
        "E-Way Bill Date": eway_date,
        "E-Way Bill Valid Upto": None,  # Not in Format 2
        "Consignor": consignor,
        "Consignee": consignee,
        "Billing Party": consignee,  # Same as Consignee
        "Delivery Address": None,  # Will be filled by delivery address extraction
        "Vehicle": vehicle,
        "Driver Mobile": driver_mobile,
        "Date (ERP entry date)": invoice_date,
        "Invoice No": invoice_no,
        "Invoice Date": invoice_date,
        "Content Name (Goods Name)": content_name,
        "Actual Weight": quantity,
        "E-Way Bill No (Goods)": eway_no,
        "Rate": rate,
        "IRN": irn,
        "GST Type": "Unregistered",
        "goods_type": goods_type,
    }
    
    # STEP 5: Extract Delivery Address using PaddleOCR (reuse from Format 1)
    logger.info("\n📍 Extracting Delivery Address (PaddleOCR)...")
    try:
        if fmt1._HAS_DELIVERY_EXTRACTOR and fmt1._extract_delivery_v2:
            da_v2 = fmt1._extract_delivery_v2(originals[0] if originals else None, pdf_path)
            if da_v2:
                if isinstance(da_v2, dict):
                    rb = da_v2.get("right_box") or da_v2.get("right_box_raw")
                    if isinstance(rb, str):
                        cleaned_rb = re.sub(r'\s{2,}', ' ', rb).strip()
                        raw_data["Delivery Address"] = cleaned_rb
                        logger.info("✓ Delivery Address extracted")
                elif isinstance(da_v2, str):
                    cleaned = re.sub(r'\s{2,}', ' ', da_v2).strip()
                    raw_data["Delivery Address"] = cleaned
                    logger.info("✓ Delivery Address extracted")
    except Exception as e:
        logger.error("✗ Delivery Address extraction failed: %s", e)
    
    logger.info("\n" + "=" * 80)
    logger.info("FORMAT 2 EXTRACTION COMPLETE")
    logger.info("=" * 80)
    logger.info("Fields extracted: %d/%d", 
                sum(1 for v in raw_data.values() if v is not None and v != ""), 
                len(raw_data))
    
    return raw_data


# -------------------------
# CLI Interface
# -------------------------
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Client 1 Format 2 Extractor (Jindal Industries)"
    )
    parser.add_argument("pdf_path", help="Path to input PDF file")
    parser.add_argument("--tesseract", dest="tesseract_cmd", help="Path to Tesseract executable")
    parser.add_argument("--poppler", dest="poppler_path", help="Path to Poppler bin folder (Windows)")
    parser.add_argument("--save-json", dest="save_raw_path", help="Path to save raw JSON output")
    
    args = parser.parse_args()
    
    try:
        result = run(
            args.pdf_path,
            tesseract_cmd=args.tesseract_cmd,
            poppler_path=args.poppler_path,
            save_raw_path=args.save_raw_path
        )
        
        print("\n" + "=" * 80)
        print("EXTRACTION RESULTS")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 80)
        print("KEY FIELDS SUMMARY")
        print("=" * 80)
        key_fields = ["Invoice No", "Invoice Date", "Consignee", "Vehicle", "E-Way Bill No", "Actual Weight"]
        for field in key_fields:
            value = result.get(field, "NOT FOUND")
            print(f"  {field}: {value}")
        
    except Exception as e:
        logger.error("FATAL ERROR: %s", e, exc_info=True)
        sys.exit(1)
