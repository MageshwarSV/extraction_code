# debug_consignee_oriental.py
import sys
import os
import fitz

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
from engine.extractors.client1_format1 import extract_consignee

pdf_path = r'c:\Users\avin4\Desktop\boostentryai ui code\test\123456789012.pdf'

# Redirect stdout to a file to avoid truncation issues
log_file = open('debug_trace_oriental.log', 'w', encoding='utf-8')
sys.stdout = log_file

print(f"Processing: {pdf_path}")
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()

print("-" * 40)
print("RAW TEXT AROUND HEADER:")
import re
header_re = re.compile(r'(?:Name\s*(?:&|and)\s*Address\s*(?:of|0f|o1|01|:)?\s*(?:Recipient|Consignee))\s*:?', re.IGNORECASE)
m = header_re.search(text)
if m:
    start = max(0, m.start() - 50)
    end = min(len(text), m.end() + 300)
    print(text[start:end])

print("-" * 40)
extracted = extract_consignee(text)
print(f"Extracted Consignee: '{extracted}'")

log_file.close()
sys.stdout = sys.__stdout__
print("Debug finished. Log written to debug_trace_oriental.log")
