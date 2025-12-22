import sys
import os
import re

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee

test_cases = [
    "Name & Address of Consignee: T RS ENTERPRISES",
    "Name & Address of Consignee: A BC ENTERPRISES",
    "Name & Address of Consignee: A TO Z ENTERPRISES", # Should NOT split "TO"
    "Name & Address of Consignee: GO TO HELL", # Should NOT split "GO", "TO"
    "Name & Address of Consignee: S L T ENTERPRISES"
]

print("Testing extract_consignee with mixed spacing inputs (expecting split):")
with open("split_output_utf8.txt", "w", encoding="utf-8") as f:
    for text in test_cases:
        extracted = extract_consignee(text)
        output_line = f"Input: '{text}' -> Extracted: '{extracted}'"
        print(output_line)
        f.write(output_line + "\n")
