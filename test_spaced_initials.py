import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee

test_cases = [
    # Case where OCR gives us "T R S" with spaces - should preserve
    """Name & Address of Recipient:
T R S ENTERPRISES
NO 41 3A J N ROAD""",
    # Case where OCR gives us "TRS" without spaces - should preserve
    """Name & Address of Recipient:
TRS ENTERPRISES
NO 41 3A J N ROAD""",
    # Mixed case
    """Name & Address of Recipient:
B N R AGENCIES""",
]

print("Testing extract_consignee with spaced initials:")
with open("test_spaced_initials_utf8.txt", "w", encoding="utf-8") as f:
    for text in test_cases:
        extracted = extract_consignee(text)
        # Replace newlines with \n for single line output
        text_display = text.replace('\n', '\\n')
        output_line = f"Input: '{text_display}' -> Extracted: '{extracted}'"
        print(output_line)
        f.write(output_line + "\n")
