# fix_poppler_var.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Rename poppler to poppler_bin in run function
# 1. Assignment
content = content.replace('poppler = _detect_poppler(poppler_path)', 'poppler_bin = _detect_poppler(poppler_path)')
# 2. Logging
content = content.replace('logger.info("✓ Using Poppler: %s", poppler)', 'logger.info("✓ Using Poppler: %s", poppler_bin)')
# 3. Usage in try block
content = content.replace('if poppler:', 'if poppler_bin:')
content = content.replace('poppler_path=poppler)', 'poppler_path=poppler_bin)')

# Also fix the debug print I added
content = content.replace('poppler variable = {poppler}', 'poppler variable = {poppler_bin}')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS: Renamed poppler to poppler_bin")
