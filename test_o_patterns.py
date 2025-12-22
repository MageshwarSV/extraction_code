import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee

test_cases = [
    # Original PO cases
    """Name & Address of Recipient:
JCS READYMIX CONCRETE
po 30/ 25-26/19.11.2025""",
    """Name & Address of Recipient:
JCS READYMIX CONCRETE po 30/ 25-26/19.11.2025""",
    """Name & Address of Recipient:
JCS READYMIX CONCRETE po""",
    """Name & Address of Recipient:
JCS READYMIX CONCRETE PO 12345""",
    # New test cases for other patterns ending with O
    """Name & Address of Recipient:
SOME COMPANY NAME QO 12345""",
    """Name & Address of Recipient:
ANOTHER COMPANY WO""",
    """Name & Address of Recipient:
TEST COMPANY EO 999""",
    # Should NOT strip "CO" as it's a valid company suffix
    """Name & Address of Recipient:
VALID COMPANY CO""",
    """Name & Address of Recipient:
VALID TRADING CO LTD"""
]

print("Testing extract_consignee with patterns ending in O:")
with open("test_o_patterns_utf8.txt", "w", encoding="utf-8") as f:
    for text in test_cases:
        extracted = extract_consignee(text)
        # Replace newlines with \n for single line output
        text_display = text.replace('\n', '\\n')
        output_line = f"Input: '{text_display}' -> Extracted: '{extracted}'"
        print(output_line)
        f.write(output_line + "\n")
