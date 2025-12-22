# debug_run.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug print before the try block
old_block = 'logger.info("PASS 1: Tesseract OCR @ DPI 300 (Slow path)")'
new_block = 'logger.info("PASS 1: Tesseract OCR @ DPI 300 (Slow path)")\n        logger.info(f"DEBUG: poppler variable = {poppler}")'

if old_block in content:
    content = content.replace(old_block, new_block)
    
    # Also modify the exception handler to print traceback
    old_except = 'except Exception as e:'
    new_except = 'except Exception as e:\n            import traceback\n            logger.error(traceback.format_exc())'
    
    content = content.replace(old_except, new_except)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added debug prints")
else:
    print("ERROR: Could not find block to replace")
