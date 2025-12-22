# revert_force_ocr.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Revert the forced OCR change
# Look for the commented out line
broken_line = 'text_layer_text = None # _extract_text_from_pdf_layer(pdf_path)'
fixed_line = 'text_layer_text = _extract_text_from_pdf_layer(pdf_path)'

if broken_line in content:
    content = content.replace(broken_line, fixed_line)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Reverted forced OCR (re-enabled text layer)")
else:
    print("WARNING: Could not find line to revert. Checking for other variants...")
    # Check if it was modified differently
    idx = content.find("text_layer_text = None")
    if idx > 0:
        print(f"Found 'text_layer_text = None' at {idx}")
