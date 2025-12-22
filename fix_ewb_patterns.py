import re

# Read the file
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the patterns section in extract_eway_bill
in_eway_function = False
patterns_start = -1
patterns_end = -1

for i, line in enumerate(lines):
    if 'def extract_eway_bill' in line:
        in_eway_function = True
    if in_eway_function and 'patterns = [' in line:
        patterns_start = i
    if in_eway_function and patterns_start > 0 and line.strip() == ']':
        patterns_end = i
        break

print(f"Found patterns at lines {patterns_start+1} to {patterns_end+1}")

if patterns_start > 0 and patterns_end > patterns_start:
    # Build new patterns section
    new_patterns = '''    patterns = [
        # ULTRA-TOLERANT: Missing letters (WB No, EB No, EW No)
        re.compile(r'W\\s*B\\s*(?:No|N0)?\\.?\\s*[:.\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        re.compile(r'E\\s*[B8]\\s*(?:No|N0)?\\.?\\s*[:.\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        re.compile(r'E\\s*W\\s*(?:No|N0)?\\.?\\s*[:.\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        re.compile(r'E\\s*W\\s*[B8]\\s*(?:N[O0o])?\\.?\\s*[:.\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        re.compile(r'W\\s*8\\s*(?:No|N0)?\\.?\\s*[:.\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        # Letter-by-letter flexible patterns
        re.compile(r'E[\\s.\\-_,|]*W[\\s.\\-_,|]*B[\\s.\\-_,|]*(?:No|Number|N[\\s.]*o)?\\.?\\s*[:\\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\\s.\\-_,|]*W[\\s.\\-_,|]*A[\\s.\\-_,|]*Y[\\s.\\-_,|]*B[\\s.\\-_,|]*I[\\s.\\-_,|]*L[\\s.\\-_,|]*L\\s*(?:No|Number|N[\\s.]*o)?\\.?\\s*[:\\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\\s.\\-_,|]*W[\\s.\\-_,|]*A[\\s.\\-_,|]*Y\\s*(?:No|Number)?\\.?\\s*[:\\-]?\\s*([0-9OIlSs|\\s]{12,})', re.IGNORECASE),
        # Original strict patterns
        re.compile(r'EWB\\s*No\\.?\\s*[:\\-]?\\s*([0-9\\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\\s\\-]*W[\\s\\-]*B\\s*(?:No|Number)\\.?\\s*[:\\-]?\\s*([0-9\\s]{12,})', re.IGNORECASE),
        re.compile(r'E[\\s\\-]*Way\\s*Bill\\s*(?:No|Number)?\\.?\\s*[:\\-]?\\s*([0-9\\s]{12,})', re.IGNORECASE),
    ]
'''
    
    # Replace the patterns section
    new_lines = lines[:patterns_start] + [new_patterns] + lines[patterns_end+1:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("SUCCESS: Patterns replaced!")
else:
    print("ERROR: Could not find patterns section")
