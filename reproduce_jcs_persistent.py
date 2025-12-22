import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from engine.extractors.client1_format1 import extract_consignee

test_cases = [
    # Case 1: PO on next line (should be handled by previous fix, but re-verifying)
    """Name & Address of Recipient:
JCS READYMIX CONCRETE
po 30/ 25-26/19.11.2025""",
    # Case 2: PO on same line (new case)
    """Name & Address of Recipient:
JCS READYMIX CONCRETE po 30/ 25-26/19.11.2025""",
    # Case 3: PO on same line with just "po"
    """Name & Address of Recipient:
JCS READYMIX CONCRETE po""",
    # Case 4: PO on same line with "PO"
    """Name & Address of Recipient:
JCS READYMIX CONCRETE PO 12345"""
]

print("Testing extract_consignee with persistent JCS inputs:")
with open("jcs_persistent_output_utf8.txt", "w", encoding="utf-8") as f:
    for text in test_cases:
        extracted = extract_consignee(text)
        # Replace newlines with \n for single line output
        text_display = text.replace('\n', '\\n')
        output_line = f"Input: '{text_display}' -> Extracted: '{extracted}'"
        print(output_line)
        f.write(output_line + "\n")
