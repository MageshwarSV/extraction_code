# force_ocr.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_line = 'text_layer_text = _extract_text_from_pdf_layer(pdf_path)'
new_line = 'text_layer_text = None # _extract_text_from_pdf_layer(pdf_path)'

if old_line in content:
    content = content.replace(old_line, new_line)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Forced OCR by disabling text layer extraction")
else:
    print("ERROR: Could not find the line to replace")
