import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Change \s+ to \s* in datetime_pat line
content = re.sub(
    r"(datetime_pat = r'\([^\)]+\[./-\]\[0-9OIlSs\]\{2,4\})\\\\s\+",
    r"\1\\s*",
    content
)

# Fix 2: Also fix the standard patterns that require space
content = content.replace(
    r"([0-9OIlSs./-]+\s+[0-9OIlSs:]{4,})",
    r"([0-9OIlSs./-]+\s*[0-9OIlSs:]{4,})"
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Fixed datetime patterns to allow optional space")
