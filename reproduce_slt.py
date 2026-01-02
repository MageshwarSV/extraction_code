import sys
import os
import re

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.odsfhiaclient1_format11_format1 import extract_consignee

test_cases = [
    "Name & Address of Consignee: SLT CEMENT MARKETERS PVT LTD",
    "Name & Address of Consignee: S L T CEMENT MARKETERS PVT LTD",
    "Name & Address of Consignee: BNR AGENCIES",
    "Name & Address of Consignee: B N R AGENCIES"
]

print("Testing extract_consignee with SLT inputs:")
with open("slt_output_utf8.txt", "w", encoding="utf-8") as f:
    for text in test_cases:
        extracted = extract_consignee(text)
        output_line = f"Input: '{text}' -> Extracted: '{extracted}'"
        print(output_line)
        f.write(output_line + "\n")
