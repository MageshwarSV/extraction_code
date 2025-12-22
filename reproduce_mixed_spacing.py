import sys
import os
import re

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee

test_cases = [
    "Name & Address of Consignee: T RS ENTERPRISES",
    "Name & Address of Consignee: T R S ENTERPRISES",
    "Name & Address of Consignee: S L T ENTERPRISES",
    "Name & Address of Consignee: A B C D E F G",
    "Name & Address of Consignee: A BC D EFG"
]

print("Testing extract_consignee with mixed spacing inputs:")
for text in test_cases:
    extracted = extract_consignee(text)
    print(f"Input: '{text}' -> Extracted: '{extracted}'")
