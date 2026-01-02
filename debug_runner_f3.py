
import sys
import os
import traceback

sys.path.insert(0, os.getcwd())

try:
    from engine.extractors.client1_format3 import extract_format3_data
    
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    print("Running extraction...")
    result = extract_format3_data(pdf_path)
    print("Status:", result.get("status"))
    if result.get("status") == "error":
        print("Error:", result.get("error_message"))
except Exception:
    traceback.print_exc()
