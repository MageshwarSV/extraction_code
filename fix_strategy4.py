# fix_strategy4.py - Update Strategy 4 fallback in extract_eway_bill
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the single line
old_line = "    all_12digit = re.findall(r'\\b([0-9]{12})\\b', text or \"\")"
new_lines = """    all_12digit = re.findall(r'\\b([0-9]{12})\\b', text or "")
    # Also find 12-digit sequences with prefix chars (OCR error like 'b124125160361')
    all_12digit_loose = re.findall(r'[^0-9]([0-9]{12})', text or "")
    all_12digit = list(set(all_12digit + all_12digit_loose))"""

if old_line in content:
    content = content.replace(old_line, new_lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated Strategy 4 fallback")
else:
    print("ERROR: Old line not found")
    # Show what's around line 1674
    lines = content.split('\n')
    print("Lines around 1674:")
    for i in range(1670, min(1680, len(lines))):
        print(f"{i+1}: {lines[i][:80]}")
