import re

def is_valid_company_name(text):
    """Check if text looks like a valid company name (updated logic)."""
    if not text or len(text) < 8:
        return False
    # Count alphabetic characters
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < len(text) * 0.5:
        return False
    # Reject if too many spaces
    space_count = text.count(' ')
    if space_count > len(text) / 3:
        return False
    # Reject weird patterns
    if re.search(r'[^A-Za-z0-9\s\(\)\-]{3,}', text):
        return False
    
    text_upper = text.upper().strip()
    suffixes = ['LTD', 'LIMITED', 'PVT LTD', 'PRIVATE LIMITED', 'PRIVATE LTD', 
                'INC', 'CORP', 'METALS', 'CEMENT', 'STEEL', 'SOLUTIONS', 
                'WORKS', 'SERVICES', 'SYSTEMS', 'TECHNOLOGIES', 'ENTERPRISES',
                'INDUSTRIES', 'INFRASTRUCTURES', 'BLUE METALS']
    
    base_name = text_upper.split('-')[0].strip() if '-' in text_upper else text_upper
    has_suffix = any(base_name.endswith(s) or text_upper.endswith(s) for s in suffixes)
    has_india_paren = '(INDIA)' in text_upper or 'INDIA)' in text_upper
    is_caps_sequence = len(text_upper.split()) >= 2 and text_upper.isupper()
    
    return has_suffix or has_india_paren or is_caps_sequence

def score_company_name(text):
    if not text: return 0
    score = min(len(text) / 5, 10)
    text_upper = text.upper()
    suffixes = ['PVT LTD', 'PRIVATE LIMITED', 'LIMITED', 'LTD', 'METALS', 'CEMENT', 'STEEL', 
                'SOLUTIONS', 'WORKS', 'SERVICES', 'TECHNOLOGIES', 'METALS']
    for s in suffixes:
        if text_upper.endswith(s):
            score += 20
            break
    if re.search(r'\([A-Z]+\)', text_upper): score += 15
    if len(text_upper.split()) >= 2 and text_upper.isupper(): score += 10
    return score

test_names = [
    "NexaWorks",
    "BlueWave Solutions",
    "UrbanStack"
]

print(f"{'Business Name':<25} | {'Valid?':<8} | {'Score':<8}")
print("-" * 45)
for name in test_names:
    valid = is_valid_company_name(name)
    score = score_company_name(name)
    print(f"{name:<25} | {str(valid):<8} | {score:<8.2f}")
