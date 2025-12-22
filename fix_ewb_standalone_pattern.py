# fix_ewb_standalone_pattern.py - Make standalone EWB pattern more lenient
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The current pattern is too strict - it requires ONLY 12 digits on the line
# But OCR might have extra chars. Let's make it more lenient

old_block = '''                # Look for 12-digit number on a line by itself (common EWB format)
                ewb_match = re.search(r'^\\s*([0-9]{12})\\s*$', ocr_text, re.MULTILINE)
                if ewb_match:
                    num = ewb_match.group(1)
                    if len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR standalone: {num}")
                        return num
                
                # Look for 12-digit near any partial EWB anchor in OCR text
                ewb_ocr = re.search(r'(?:E[\\s.\\-]*W[\\s.\\-]*B|WB|EB)[\\s.\\-:]*(?:No|N0)?[\\s.\\-:]*([0-9]{12})', ocr_text, re.IGNORECASE)
                if ewb_ocr:
                    num = ewb_ocr.group(1)
                    if len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR with anchor: {num}")
                        return num'''

new_block = '''                # Look for 12-digit number on a line (can have trailing chars)
                ewb_match = re.search(r'^[^0-9]*([0-9]{12})[^0-9]*$', ocr_text, re.MULTILINE)
                if ewb_match:
                    num = ewb_match.group(1)
                    if len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR standalone: {num}")
                        return num
                
                # Look for any 12-digit number in OCR text that starts with 5/1/3 (common EWB prefixes)
                all_12 = re.findall(r'([0-9]{12})', ocr_text)
                for num in all_12:
                    if num[0] in '513' and len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR scan (priority prefix): {num}")
                        return num
                
                # Fallback: Any valid 12-digit
                for num in all_12:
                    if len(set(num)) > 3 and not _looks_like_datetime(num):
                        logger.debug(f"  [E-Way] Found via OCR scan (any): {num}")
                        return num'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated OCR-first patterns to be more lenient")
else:
    print("ERROR: Old block not found")
