# fix_ewb_ocr_priority.py - Prioritize OCR for EWB when text layer is unreliable
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add a check in Strategy 4 fallback to prefer OCR-detected numbers over text layer numbers
# By checking if the found number has EWB anchor nearby

# Look for the Strategy 4 section and enhance it
old_strategy4 = '''    # Strategy 4: Smart Fallback - VERY SELECTIVE
    # Look for 12-digit numbers that are clearly E-Way Bills
    # Also search without word boundaries (OCR may append letters like 'b124125160361')
    all_12digit = re.findall(r'\\b([0-9]{12})\\b', text or "")
    # Also find 12-digit sequences with prefix chars (OCR error like 'b124125160361')
    all_12digit_loose = re.findall(r'[^0-9]([0-9]{12})', text or "")
    all_12digit = list(set(all_12digit + all_12digit_loose))
    candidates = []'''

new_strategy4 = '''    # Strategy 4: Smart Fallback with 11-digit recovery
    # PRIORITY 1: Look for 11-digit numbers near EWB anchor (OCR may drop leading digit)
    ewb_11digit = re.search(r'(?:E[\s.\-]*W[\s.\-]*B|WB|EB)[\s.\-:]*(?:No|N0)?[\s.\-:]*([0-9]{11})\\b', text or "", re.IGNORECASE)
    if ewb_11digit:
        candidate_11 = ewb_11digit.group(1)
        # EWB numbers typically start with 1 or 5, try prepending
        for prefix in ['5', '1']:
            candidate_12 = prefix + candidate_11
            if len(set(candidate_12)) > 3 and not _looks_like_datetime(candidate_12):
                logger.debug(f"  [E-Way] Recovered 12-digit from 11-digit: {candidate_12}")
                return candidate_12
    
    # PRIORITY 2: Look for 12-digit numbers with NEARBY EWB anchor (not just any 12-digit)
    ewb_context = re.search(r'(?:E[\s.\-]*W[\s.\-]*B|WB|EB|Way\s*Bill)[\s.\-:]*(?:No|N0)?[\s.\-:]*([0-9]{12})\\b', text or "", re.IGNORECASE)
    if ewb_context:
        candidate = ewb_context.group(1)
        if len(set(candidate)) > 3 and not _looks_like_datetime(candidate):
            logger.debug(f"  [E-Way] Found 12-digit with EWB anchor: {candidate}")
            return candidate
    
    # PRIORITY 3: Any 12-digit number (last resort)
    all_12digit = re.findall(r'\\b([0-9]{12})\\b', text or "")
    all_12digit_loose = re.findall(r'[^0-9]([0-9]{12})', text or "")
    all_12digit = list(set(all_12digit + all_12digit_loose))
    candidates = []'''

if old_strategy4 in content:
    content = content.replace(old_strategy4, new_strategy4)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated Strategy 4 with 11-digit recovery and EWB anchor priority")
else:
    print("ERROR: Old Strategy 4 not found. Checking content...")
    # Check what's there
    idx = content.find("Strategy 4")
    if idx > 0:
        print("Found Strategy 4 at char", idx)
        print("Snippet:", content[idx:idx+400])
    else:
        print("Strategy 4 not found at all")
