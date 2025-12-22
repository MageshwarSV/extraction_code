# fix_ewb_null_check.py - Add null check for ocr_images in OCR-first block
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The iteration needs a safety check
old_iter = '''    if not has_ewb_anchor:
        logger.debug("  [E-Way] Text layer has no EWB anchor, trying OCR first...")
        # Try to extract from OCR images first
        for img in ocr_images[:1]:  # Just first page'''

new_iter = '''    if not has_ewb_anchor and ocr_images:
        logger.debug("  [E-Way] Text layer has no EWB anchor, trying OCR first...")
        # Try to extract from OCR images first
        for img in (ocr_images or [])[:1]:  # Just first page'''

if old_iter in content:
    content = content.replace(old_iter, new_iter)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added null check for ocr_images")
else:
    print("ERROR: Old block not found")
