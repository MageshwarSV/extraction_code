# fix_poppler_path.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update Poppler path
old_line = 'poppler_bin = _detect_poppler(poppler_path)'
new_line = 'poppler_path = r"C:\\poppler-25.07.0\\Library\\bin"\n    poppler_bin = _detect_poppler(poppler_path)'

if old_line in content:
    content = content.replace(old_line, new_line)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated Poppler path")
else:
    print("ERROR: Could not find line to replace")
