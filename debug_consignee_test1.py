# debug_consignee_test1.py
import sys
import os
import fitz

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
from engine.extractors.odsfhiaclient1_format11_format1 import extract_consignee

pdf_path = r'c:\Users\avin4\Desktop\boostentryai ui code\test\test1.pdf'

# Redirect stdout to a file to avoid truncation issues
log_file = open('debug_trace.log', 'w', encoding='utf-8')
sys.stdout = log_file

print(f"Processing: {pdf_path}")
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()

print("-" * 40)
extracted = extract_consignee(text)
print(f"Extracted Consignee: '{extracted}'")

log_file.close()
sys.stdout = sys.__stdout__
print("Debug finished. Log written to debug_trace.log")
