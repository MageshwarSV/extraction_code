import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee

test_cases = [
    """Name & Address of Recipient :
AVS Tech Building Solutions I
Pvt Ltd.
I Floor NO 298 AVS House
Place of Supply: Hosur""",
    """Name & Address of Recipient :
AVS Tech Building Solutions I
Pvt Ltd."""
]

print("Testing extract_consignee with AVS Tech inputs:")
with open("avs_output_utf8.txt", "w", encoding="utf-8") as f:
    for text in test_cases:
        extracted = extract_consignee(text)
        # Replace newlines with \n for single line output
        text_display = text.replace('\n', '\\n')
        output_line = f"Input: '{text_display}' -> Extracted: '{extracted}'"
        print(output_line)
        f.write(output_line + "\n")
