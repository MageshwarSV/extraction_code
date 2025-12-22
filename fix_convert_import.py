# fix_convert_import.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the import issue by adding explicit import inside the run function
# Find the try block where convert_from_path is called
old_block = 'try:\n            if poppler_bin:'
new_block = 'try:\n            from pdf2image import convert_from_path\n            if poppler_bin:'

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added explicit import for convert_from_path")
else:
    print("ERROR: Could not find block to replace")
