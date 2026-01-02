
import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

# Import the extractor module
from engine.extractors import client1_format1

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_fn_fix():
    print("Testing FN -> TN Fix...")
    
    # Test cases
    cases = [
        ("Vehicle No: FN45BQ0372", "TN45BQ0372"),  # FN -> TN
        ("Vehicle No: TN45BQ0372", "TN45BQ0372"),  # TN -> TN (no change)
        ("Vehicle No: KA01AN0922", "KA01AN0922"),  # KA -> KA (no change)
        ("Vehicle No: FN18K7553", "TN18K7553"),   # FN -> TN
    ]
    
    for input_text, expected in cases:
        print(f"\nInput: '{input_text}'")
        extracted = client1_format1.extract_vehicle(input_text)
        print(f"Extracted: '{extracted}'")
        
        if extracted == expected:
            print("✅ PASS")
        else:
            print(f"❌ FAIL (Expected {expected})")

if __name__ == "__main__":
    test_fn_fix()
