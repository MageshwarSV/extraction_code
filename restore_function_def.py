# restore_function_def.py
filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Look for the orphaned code block start
target_line_idx = -1
for i, line in enumerate(lines):
    if '# 2. Check for "garbage" indicators' in line:
        # Go back a few lines to find where the function *should* start
        # The previous attempt inserted the body but missed the def.
        # Let's look for where the previous function `_is_company_line` ends.
        target_line_idx = i
        break

if target_line_idx != -1:
    # We found the middle of the inserted code.
    # The code I inserted via fix_consignee_cleaning.py started with:
    # "        # 1. Explicitly split by common separators..."
    # Let's find that line.
    start_idx = -1
    for i in range(target_line_idx, max(0, target_line_idx - 20), -1):
        if 'Explicitly split by common separators' in lines[i]:
            start_idx = i
            break
    
    if start_idx != -1:
        # We found the start of the inserted block.
        # We need to insert the def line BEFORE this block.
        # But wait, the previous code might have been:
        # def _clean_company_line(raw: str) -> Optional[str]:
        #     s = (raw or "").strip(" :-\t")
        #     ...
        
        # If I replaced the *body*, the def line might still be there?
        # Let's check the lines before start_idx.
        print(f"Checking lines before {start_idx}:")
        print(lines[start_idx-1])
        print(lines[start_idx-2])
        print(lines[start_idx-3])
        
        # If the def line is missing, we insert it.
        if 'def _clean_company_line' not in lines[start_idx-1] and 'def _clean_company_line' not in lines[start_idx-2]:
             # Insert the def line and the initial s = ... lines which seem to be missing based on my previous view
             # Wait, the previous view showed:
             # 620:                 
             # 621:                 # 2. Check for "garbage" indicators...
             
             # This implies the code I see in the view is ONLY the middle part of the function?
             # Or did I overwrite the top part?
             
             # Let's just rewrite the whole function using the known start and end points of the file.
             # I know `_is_company_line` ends before this.
             pass

# Alternative: Read the file, find `_is_company_line`, find where it ends, and then overwrite everything until `m_stop = stop_tokens.search(s)` with the CORRECT full function body.

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find end of _is_company_line
is_company_end = content.find('return True', content.find('def _is_company_line'))
if is_company_end == -1:
    print("ERROR: Could not find _is_company_line end")
    exit(1)

# Find start of the tail part that seems correct (m_stop...)
tail_start = content.find('m_stop = stop_tokens.search(s)')
if tail_start == -1:
    print("ERROR: Could not find tail start")
    exit(1)

# The gap between them is where _clean_company_line should be.
# Let's grab the content before and after.
# Note: _is_company_line is inside extract_consignee, so indentation is 4 spaces.
# _clean_company_line is also inside, so indentation is 4 spaces.

# Find the exact end of _is_company_line block (it ends with return True inside an if, or just the last return True)
# Actually, let's look for the start of the messed up block.
bad_block_start = content.find('# 1. Explicitly split by common separators')
if bad_block_start == -1:
     # Maybe it's the "garbage" line
     bad_block_start = content.find('# 2. Check for "garbage" indicators')

if bad_block_start != -1:
    # We found the bad block.
    # We need to insert the function def before it?
    # No, the bad block is likely missing the top part of the function.
    
    # Let's define the FULL correct function body again.
    full_function = '''    def _clean_company_line(raw: str) -> Optional[str]:
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
                s = parts[0]
        
'''
    # Now we need to find where to put it.
    # It should go after _is_company_line and before m_stop...
    # But wait, m_stop is part of _clean_company_line!
    # So I need to splice it in correctly.
    
    # Let's find the previous function end
    prev_func_end = content.rfind('return True', 0, bad_block_start)
    # Find the start of the tail (m_stop)
    tail_start = content.find('m_stop = stop_tokens.search(s)', bad_block_start)
    
    if prev_func_end != -1 and tail_start != -1:
        # Adjust indices to capture the full range to replace
        # We want to keep 'return True' line, so start after it
        replace_start = content.find('\n', prev_func_end) + 1
        
        # We want to replace everything up to tail_start
        replace_end = tail_start
        
        new_content = content[:replace_start] + '\n' + full_function + content[replace_end:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("SUCCESS: Restored function definition and body")
    else:
        print("ERROR: Could not calculate replacement range")

