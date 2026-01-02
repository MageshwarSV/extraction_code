import re

def is_valid_company_name(text):
    if not text or len(text) < 5:
        return False
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < len(text) * 0.6:
        return False
    space_count = text.count(' ')
    if space_count > len(text) / 4:
        return False
    if re.search(r'[^A-Za-z0-9\s\(\)\-]{3,}', text):
        return False
    suffixes = ['LTD', 'LIMITED', 'PVT', 'PRIVATE', 'INC', 'CORP', 'INDIA', 'METALS', 'CEMENT', 'STEEL']
    has_suffix = any(s in text.upper() for s in suffixes)
    return has_suffix or (len(text) > 10 and alpha_count > 10)

tests = [
    'SRI MAHALAKSHMI BLUE METALS',
    'SANITINGTA) BUILT WELL PVT LTD',
    'E | INDIA Os FREE See heer',
    'ee ee ee ee eee ONES',
]

for test in tests:
    alpha_count = sum(1 for c in test if c.isalpha())
    space_count = test.count(' ')
    print(f"{test}")
    print(f"  alpha: {alpha_count}, ratio: {alpha_count/len(test):.2f}")
    print(f"  spaces: {space_count}, limit: {len(test)/4:.1f}")
    print(f"  valid: {is_valid_company_name(test)}")
    print()
