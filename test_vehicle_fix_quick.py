#!/usr/bin/env python
"""Quick test for the _fix_oversized_vehicle function"""

import sys
sys.path.insert(0, r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.client1_format1 import _fix_oversized_vehicle

# Test cases: oversized plates that should be fixed
test_cases = [
    # Format: (input, expected_output, description)
    ("TN23AMS5290", "TN23AM5290", "S looks like 5 - remove S from end of series"),
    ("KA01LAN0922", "KA01AN0922", "L at start of series looks like 1 - remove L"),
    # Already valid - no change
    ("TN45BQ0372", "TN45BQ0372", "Already 10 chars - no change"),
    ("KA01AN0922", "KA01AN0922", "Already 10 chars - no change"),
    ("TN18K7553", "TN18K7553", "Already 9 chars - no change"),
]

print("Testing _fix_oversized_vehicle function")
print("=" * 70)

passed = 0
failed = 0

for test in test_cases:
    input_plate, expected, description = test
    result = _fix_oversized_vehicle(input_plate)
    status = "✓" if result == expected else "✗"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"\n{status} {description}")
    print(f"  Input:    {input_plate:15} ({len(input_plate)} chars)")
    print(f"  Expected: {expected:15} ({len(expected)} chars)")
    print(f"  Got:      {result:15} ({len(result)} chars)")

print("\n" + "=" * 70)
print(f"Results: {passed} passed, {failed} failed")
