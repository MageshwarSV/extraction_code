# fix_invoice_patterns.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Old patterns section
old_patterns = '''    # ONLY extract from D.I.NO.& Date format (as requested by client)
    patterns = [
        # D.I.NO.& Date: 6978023250 & 14.09.2025
        r'D[.\\s]*I[.\\s]*N[O0][.\\s]*[&\\s]*Date[:\\s]*([0-9OIlSs\\s]{6,})',
        r'D[.\\s]*[I1L][.\\s]*(?:[IL1][.\\s]*)?N[O0][.\\s]*(?:&\\s*DATE)?[:\\-\\s]*([0-9OIlSs\\s]{6,})',
        r'\\bD[.\\s]*I[.\\s]*N[O0][.\\s]*[:\\-\\s]*([0-9OIlSs\\s]{6,})',
    ]'''

# New patterns section with all OCR variants (but NOT D.O)
new_patterns = '''    # ONLY extract from D.I.NO.& Date format (as requested by client)
    # FLEXIBLE: Handle OCR variants (D.LNO, D.ANO, DINO, etc.) but NOT D.O
    patterns = [
        # D.I.NO.& Date: 6978023250 & 14.09.2025 (standard)
        r'D[.\\s]*I[.\\s]*N[O0][.\\s]*[&\\s]*Date[:\\s]*([0-9OIlSs\\s]{6,})',
        
        # D.LNO (L misread from I)
        r'D[.\\s]*L[.\\s]*N[O0][.\\s]*[&\\s]*(?:Date)?[:\\-\\s]*([0-9OIlSs\\s]{6,})',
        
        # D.ANO (A misread from I)
        r'D[.\\s]*A[.\\s]*N[O0][.\\s]*[&\\s]*(?:Date)?[:\\-\\s]*([0-9OIlSs\\s]{6,})',
        
        # DINO, DLNO, DANO (no periods)
        r'\\bD[ILAY][.\\s]*N[O0][.\\s]*[&\\s]*(?:Date)?[:\\-\\s]*([0-9OIlSs\\s]{6,})',
        
        # D.1.NO (1 misread from I)
        r'D[.\\s]*1[.\\s]*N[O0][.\\s]*[&\\s]*(?:Date)?[:\\-\\s]*([0-9OIlSs\\s]{6,})',
        
        # Generic with character classes for I/L/A/1
        r'D[.\\s]*[I1LA][.\\s]*(?:[IL1][.\\s]*)?N[O0][.\\s]*(?:&\\s*DATE)?[:\\-\\s]*([0-9OIlSs\\s]{6,})',
        r'\\bD[.\\s]*I[.\\s]*N[O0][.\\s]*[:\\-\\s]*([0-9OIlSs\\s]{6,})',
    ]'''

if old_patterns in content:
    content = content.replace(old_patterns, new_patterns)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated invoice patterns with OCR variants")
else:
    print("ERROR: Could not find old patterns")
    # Try to find partial match
    if "D.I.NO.& Date format" in content:
        print("Found partial match: 'D.I.NO.& Date format'")
    else:
        print("No match found at all")
