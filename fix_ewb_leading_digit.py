# fix_ewb_leading_digit.py - Fix OCR missing leading digit in EWB number
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the "Try patterns on original text first" comment and add a pre-processing step
# to fix 11-digit EWB numbers that are missing a leading digit

# Add a new pattern that captures 11-digit numbers near EWB keywords
old_code = '''    # Try patterns on original text first (don't normalize full text - that would change B->8, o->0 in keywords!)
    for pat in patterns:'''

new_code = '''    # PRE-PROCESSING: Handle OCR dropping leading digits (e.g., "41887714126" should be "541887714126")
    # Look for 11-digit numbers near EWB that might be missing leading 5/1
    ewb_11digit = re.search(r'(?:E[\s.\-]*W[\s.\-]*B|WB|EB)[\s.\-:]*(?:No|N0)?[\s.\-:]*([0-9]{11})\b', text or "", re.IGNORECASE)
    if ewb_11digit:
        candidate_11 = ewb_11digit.group(1)
        # EWB numbers typically start with 1 or 5, try prepending
        for prefix in ['5', '1']:
            candidate_12 = prefix + candidate_11
            if len(set(candidate_12)) > 3 and not _looks_like_datetime(candidate_12):
                logger.debug(f"  [E-Way] Recovered 12-digit from 11-digit by adding prefix {prefix}: {candidate_12}")
                return candidate_12

    # Try patterns on original text first (don't normalize full text - that would change B->8, o->0 in keywords!)
    for pat in patterns:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added 11-digit recovery logic for EWB extraction")
else:
    print("ERROR: Target code not found")
    # Show snippet around line 1535
    lines = content.split('\n')
    print("Lines around 1535:")
    for i in range(1530, min(1545, len(lines))):
        print(f"{i+1}: {lines[i][:80]}")
