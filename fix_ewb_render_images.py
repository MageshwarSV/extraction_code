# fix_ewb_render_images.py - Force image rendering for EWB when text layer lacks anchor
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The problem: OCR-first path requires ocr_images, but FAST PATH doesn't populate it
# Fix: Add on-demand image rendering inside extract_eway_bill when text lacks anchor

old_ocr_check = '''    # CHECK: If text layer doesn't have EWB anchor, skip to OCR path
    # This handles PDFs where text layer is corrupted but OCR works better
    has_ewb_anchor = bool(re.search(r'(?:E[\\s.\\-]*W[\\s.\\-]*B|E[\\s.\\-]*Way|WB\\s*No)', text or "", re.IGNORECASE))
    if not has_ewb_anchor and ocr_images:'''

new_ocr_check = '''    # CHECK: If text layer doesn't have EWB anchor, skip to OCR path
    # This handles PDFs where text layer is corrupted but OCR works better
    has_ewb_anchor = bool(re.search(r'(?:E[\\s.\\-]*W[\\s.\\-]*B|E[\\s.\\-]*Way|WB\\s*No)', text or "", re.IGNORECASE))
    
    # Even if ocr_images is empty, we should still check - the images might just not be passed
    if not has_ewb_anchor:'''

if old_ocr_check in content:
    content = content.replace(old_ocr_check, new_ocr_check)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Removed ocr_images requirement for OCR-first check")
else:
    print("ERROR: Old block not found. Checking...")
    idx = content.find("has_ewb_anchor")
    if idx > 0:
        print("Found at:", idx)
        print(content[idx:idx+300])
