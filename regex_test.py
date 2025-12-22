import re

text = "AVS Tech Building Solutions I IPL/HSR/2526/108/25.10.2025 AVS Tech Building Solutions In Pvt Ltd"
regex = r'\b[A-Z]{2,6}(?:/[A-Z0-9\-\./]+)+\b'

print(f"Text: {text}")
print(f"Regex: {regex}")

match = re.search(regex, text)
if match:
    print(f"Match found: '{match.group(0)}'")
    replaced = re.sub(regex, ' ', text)
    print(f"Replaced: '{replaced}'")
    
    # Test splitting
    parts = re.split(regex, text)
    print(f"Split parts: {parts}")
else:
    print("No match found")
