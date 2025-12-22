# fix_consignee_cleaning.py
import re

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The new function body
new_function = '''    def _clean_company_line(raw: str) -> Optional[str]:
        s = (raw or "").strip(" :-\\t")
        
        # Remove OCR garbage characters
        s = re.sub(r'[_\[\]\{\}\|]+', ' ', s)
        
        # 1. Explicitly split by common separators (dates, long codes, double spaces)
        # This handles: "Garbage Code 12/12/2025 Real Company Pvt Ltd"
        # Regex matches: Dates (DD.MM.YYYY), Codes (ABC/123), or multiple spaces
        split_pat = r'(?:\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\s+)|(?:\s+[A-Z0-9]{2,10}(?:/[A-Z0-9\-\./]+)+\s+)|(?:\s{2,})'
        
        parts = re.split(split_pat, s)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) > 1:
            # Score parts: prefer ones with "Pvt", "Ltd", etc.
            def _score_part(p):
                # 1. Check for strong company suffix
                has_suffix = 1.0 if re.search(r'\\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING|INFRASTRUCTURE|PROJECTS|BUILDERS)\\b', p, re.IGNORECASE) else 0.0
                
                # 2. Check for "garbage" indicators (too many numbers, short length)
                p_clean = re.sub(r'\\d|[^A-Za-z]', '', p)
                alpha_len = len(p_clean)
                total_len = len(p)
                alpha_ratio = alpha_len / total_len if total_len > 0 else 0
                
                # Penalize very short parts or low alpha ratio
                penalty = 0.0
                if total_len < 4: penalty += 0.5
                if alpha_ratio < 0.5: penalty += 0.5
                
                return (has_suffix, alpha_ratio, -penalty)
            
            parts.sort(key=_score_part, reverse=True)
            s = parts[0]
            
        # Fallback cleanup if no split happened or after selection
        s = re.sub(r'\\d{1,2}[./-]\\d{1,2}[./-]\\d{2,4}', ' ', s)
        s = re.sub(r'Recipient\\s+Code\\s*[:\\-]\\s*\\S+', ' ', s, flags=re.IGNORECASE)
        
        # If pipe-separated segments exist (legacy check)
        if '|' in s:
            parts = [p.strip() for p in s.split('|') if p.strip()]
            if parts:
                # Reuse scoring logic if possible, or simple length/alpha
                parts.sort(key=lambda p: len(p), reverse=True) 
                s = parts[0]'''

# Find the start of the function
start_marker = 'def _clean_company_line(raw: str) -> Optional[str]:'
start_idx = content.find(start_marker)

if start_idx == -1:
    print("ERROR: Could not find function start")
    exit(1)

# Find the end of the function (heuristically, look for next function or dedent)
# The function ends before 's = re.sub(r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', ' ', s)' which is part of the original tail
# Actually, I want to replace the whole logic block down to the legacy pipe check or just replace the whole function if possible.
# But replacing the whole function is risky with indentation.
# Let's replace the specific block identified in previous attempts.

block_start = '        # Remove embedded code-like tokens'
block_end = '                parts.sort(key=_score_part, reverse=True)\n                s = parts[0]'

# Construct the replacement block
replacement = '''        # 1. Explicitly split by common separators (dates, long codes, double spaces)
        # This handles: "Garbage Code 12/12/2025 Real Company Pvt Ltd"
        # Regex matches: Dates (DD.MM.YYYY), Codes (ABC/123), or multiple spaces
        split_pat = r'(?:\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\s+)|(?:\s+[A-Z0-9]{2,10}(?:/[A-Z0-9\-\./]+)+\s+)|(?:\s{2,})'
        
        parts = re.split(split_pat, s)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) > 1:
            # Score parts: prefer ones with "Pvt", "Ltd", etc.
            def _score_part(p):
                # 1. Check for strong company suffix
                has_suffix = 1.0 if re.search(r'\\b(PVT|PRIVATE|LTD|LIMITED|LLP|COMPANY|TRADING|INFRASTRUCTURE|PROJECTS|BUILDERS)\\b', p, re.IGNORECASE) else 0.0
                
                # 2. Check for "garbage" indicators (too many numbers, short length)
                p_clean = re.sub(r'\\d|[^A-Za-z]', '', p)
                alpha_len = len(p_clean)
                total_len = len(p)
                alpha_ratio = alpha_len / total_len if total_len > 0 else 0
                
                # Penalize very short parts or low alpha ratio
                penalty = 0.0
                if total_len < 4: penalty += 0.5
                if alpha_ratio < 0.5: penalty += 0.5
                
                return (has_suffix, alpha_ratio, -penalty)
            
            parts.sort(key=_score_part, reverse=True)
            s = parts[0]'''

# We need to find the range to replace.
# The original code had:
#         # Remove embedded code-like tokens...
#         ...
#                 parts.sort(key=_score_part, reverse=True)
#                 s = parts[0]

# Let's try to match the start and end in the content
s_idx = content.find(block_start)
e_idx = content.find(block_end)

if s_idx != -1 and e_idx != -1:
    e_idx += len(block_end)
    # Perform replacement
    new_content = content[:s_idx] + replacement + content[e_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Replaced cleaning logic")
else:
    print("ERROR: Could not find block boundaries")
    print(f"Start found: {s_idx != -1}")
    print(f"End found: {e_idx != -1}")
