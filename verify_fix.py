import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.(working)client1_format1 import extract_consignee

text = "Name & Address of Recipient : AVS Tech Building Solutions I IPL/HSR/2526/108/25.10.2025 AVS Tech Building Solutions In Pvt Ltd"

print(f"Input Text: {text}")
extracted = extract_consignee(text)
print(f"Extracted Consignee: '{extracted}'")

expected = "AVS Tech Building Solutions In Pvt Ltd"
if extracted and expected.lower() in extracted.lower():
    print("SUCCESS: Extracted value matches expected.")
else:
    print(f"FAILURE: Expected '{expected}', got '{extracted}'")
