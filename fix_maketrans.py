import re

# Read the file
with open(r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the problematic normalize_for_dates function
old_function = """def normalize_for_dates(s: str) -> str:
    \"\"\"Normalize OCR artifacts in date strings\"\"\"
    trans = str.maketrans({
        'O': '0', 'o': '0', 'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5', 'B': '8',
        '—': '-', '–': '-', '‚': ','
    })
    return s.translate(trans)"""

new_function = """def normalize_for_dates(s: str) -> str:
    \"\"\"Normalize OCR artifacts in date strings\"\"\"
    # Single-character mappings only
    trans = str.maketrans({
        'O': '0', 'o': '0', 'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5', 'B': '8'
    })
    s = s.translate(trans)
    
    # Multi-character Unicode replacements (manual)
    s = s.replace('—', '-')  # em dash
    s = s.replace('–', '-')  # en dash
    s = s.replace('‚', ',')  # low quotation mark
    
    return s"""

# Replace
if old_function in content:
    content = content.replace(old_function, new_function)
    print("✓ Fixed normalize_for_dates function!")
else:
    print("✗ Could not find exact function match, trying pattern-based replacement...")
    # Try pattern-based replacement
    pattern = r"(def normalize_for_dates\(s: str\) -> str:.*?trans = str\.maketrans\({[^}]+}\).*?return s\.translate\(trans\))"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content.replace(match.group(0), new_function)
        print("✓ Fixed using pattern match!")
    else:
        print("✗ Pattern match failed")

# Write back
with open(r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ File updated successfully!")
