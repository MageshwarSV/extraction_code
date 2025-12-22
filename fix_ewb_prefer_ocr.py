# fix_ewb_prefer_ocr.py - Make EWB extraction prefer OCR when text layer is unreliable
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the beginning of extract_eway_bill function and add a check:
# If text doesn't contain EWB anchor, prefer OCR path

old_start = '''def extract_eway_bill(text: str, ocr_images: Optional[List[Image.Image]] = None) -> Optional[str]:
    r"""
    Extract E-Way Bill number - ENHANCED for smudged/mixed/tilted OCR
    Combines text search + targeted OCR on E-Way Bill region
    Uses letter-by-letter pattern matching to handle smudged characters
    """
    
    # Build flexible patterns using letter-by-letter matching
    ewb_flex = _build_flexible_pattern("EWB")
    eway_flex = _build_flexible_pattern("EWAY")
    way_flex = _build_flexible_pattern("WAY")
    bill_flex = _build_flexible_pattern("BILL")'''

new_start = '''def extract_eway_bill(text: str, ocr_images: Optional[List[Image.Image]] = None) -> Optional[str]:
    r"""
    Extract E-Way Bill number - ENHANCED for smudged/mixed/tilted OCR
    Combines text search + targeted OCR on E-Way Bill region
    Uses letter-by-letter pattern matching to handle smudged characters
    """
    
    # CHECK: If text layer doesn't have EWB anchor, skip to OCR path
    # This handles PDFs where text layer is corrupted but OCR works better
    has_ewb_anchor = bool(re.search(r'(?:E[\s.\-]*W[\s.\-]*B|E[\s.\-]*Way|WB\s*No)', text or "", re.IGNORECASE))
    if not has_ewb_anchor and ocr_images:
        logger.debug("  [E-Way] Text layer has no EWB anchor, trying OCR first...")
        # Try to extract from OCR images first
        for img in ocr_images[:1]:  # Just first page
            try:
                from PIL import ImageOps
                gray = ImageOps.autocontrast(img.convert("L"))
                ocr_text = pytesseract.image_to_string(gray, config="--oem 1 --psm 6")
                
                # Look for 12-digit number on a line by itself (common EWB format)
                ewb_match = re.search(r'^\\s*([0-9]{12})\\s*$', ocr_text, re.MULTILINE)
                if ewb_match:
                    num = ewb_match.group(1)
                    if len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR standalone: {num}")
                        return num
                
                # Look for 12-digit near any partial EWB anchor in OCR text
                ewb_ocr = re.search(r'(?:E[\s.\-]*W[\s.\-]*B|WB|EB)[\s.\-:]*(?:No|N0)?[\s.\-:]*([0-9]{12})', ocr_text, re.IGNORECASE)
                if ewb_ocr:
                    num = ewb_ocr.group(1)
                    if len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR with anchor: {num}")
                        return num
            except Exception as e:
                logger.debug(f"  [E-Way] OCR first-pass failed: {e}")
    
    # Build flexible patterns using letter-by-letter matching
    ewb_flex = _build_flexible_pattern("EWB")
    eway_flex = _build_flexible_pattern("EWAY")
    way_flex = _build_flexible_pattern("WAY")
    bill_flex = _build_flexible_pattern("BILL")'''

if old_start in content:
    content = content.replace(old_start, new_start)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added OCR-first path when text layer lacks EWB anchor")
else:
    print("ERROR: Old function start not found")
    # Check what's there
    idx = content.find("def extract_eway_bill")
    if idx > 0:
        print("Found at char", idx)
        print("Snippet:", content[idx:idx+500])
