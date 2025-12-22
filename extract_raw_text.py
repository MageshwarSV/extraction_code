# extract_raw_text.py
import fitz
import sys

pdf_path = r'c:\Users\avin4\Desktop\boostentryai ui code\test\test1.pdf'
doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()

with open('raw_text.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print(f"Extracted {len(text)} chars to raw_text.txt")
