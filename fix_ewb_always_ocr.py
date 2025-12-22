# fix_ewb_always_ocr.py - Make EWB extraction ALWAYS use OCR (skip text layer)
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the call to extract_eway_bill and modify it to use OCR
# Line 2688: eway_no = extract_eway_bill(text, originals)

old_call = '''    eway_no = extract_eway_bill(text, originals)  # Pass images for enhanced OCR
    if not eway_no:
        # Debug: Check if we can find any E-Way Bill-like patterns
        eway_debug = re.findall(r'(?:E-?Way|EWB).*?[0-9]{8,}', text, re.IGNORECASE)
        if eway_debug:
            logger.debug("  [E-Way Debug] Found E-Way-like patterns: %s", eway_debug[:3])
    logger.info("  E-Way Bill No: %s", eway_no or "NOT FOUND")'''

new_call = '''    # EWB extraction: ALWAYS use OCR for accuracy (text layer often corrupted)
    if not originals:
        # Render images if not available (FAST PATH was used)
        logger.info("  [E-Way] Rendering images for OCR-based extraction...")
        try:
            from pdf2image import convert_from_path
            poppler_bin = _detect_poppler(None)
            originals = convert_from_path(
                pdf_path,
                dpi=300,
                poppler_path=poppler_bin,
                first_page=1,
                last_page=1
            )
            logger.info("  [E-Way] Loaded %d image(s) for OCR", len(originals))
        except Exception as img_err:
            logger.warning("  [E-Way] Could not render images: %s", img_err)
    
    eway_no = extract_eway_bill(text, originals)  # Pass images for OCR-based extraction
    if not eway_no:
        # Debug: Check if we can find any E-Way Bill-like patterns
        eway_debug = re.findall(r'(?:E-?Way|EWB).*?[0-9]{8,}', text, re.IGNORECASE)
        if eway_debug:
            logger.debug("  [E-Way Debug] Found E-Way-like patterns: %s", eway_debug[:3])
    logger.info("  E-Way Bill No: %s", eway_no or "NOT FOUND")'''

if old_call in content:
    content = content.replace(old_call, new_call)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: EWB extraction now always renders images for OCR")
else:
    print("ERROR: Old call not found")
    # Check what's there
    idx = content.find("eway_no = extract_eway_bill")
    if idx > 0:
        print("Found at:", idx)
        print("Snippet:", content[idx:idx+200])
