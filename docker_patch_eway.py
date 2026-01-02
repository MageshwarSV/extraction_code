"""
Patch script to modify extract_eway_bill in Docker
Run this INSIDE Docker container
"""

import re

# Read the current file
with open('/app/engine/extractors/client1_format1.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line where extract_eway_bill is defined and add fix after docstring
# We'll insert our priority check right after the docstring

# Pattern to find the function and its docstring
pattern = r'(def extract_eway_bill\(text: str, ocr_images: Optional\[List\[Image\.Image\]\] = None\) -> Optional\[str\]:.*?""")\s*\n(\s*# Build flexible patterns)'

replacement = r'''\1

    # DOCKER FIX: Try direct 12-digit pattern FIRST (most reliable)
    # This prevents image-based OCR issues due to Poppler rendering differences
    direct_12digit = re.findall(r'\\b([0-9]{12})\\b', text or "")
    for num in direct_12digit:
        if not _looks_like_datetime(num) and len(set(num)) > 3:
            idx = (text or "").find(num)
            if idx >= 0:
                context = (text[max(0, idx-50):idx+20] if text else "").upper()
                if any(kw in context for kw in ['EWB', 'EWAY', 'E-WAY', 'EWE']):
                    logger.debug(f"  [E-Way] Found via direct pattern (Docker priority): {num}")
                    return num

    \2'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

if new_content != content:
    with open('/app/engine/extractors/client1_format1.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Modified extract_eway_bill to prefer direct pattern in Docker")
else:
    print("ERROR: Pattern not found or already modified")
