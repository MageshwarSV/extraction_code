
import sys
import os
import logging

# Setup path to import engine
sys.path.append(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.odsfhiaclient1_format11_format1 import extract_vehicle

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_extraction():
    # Test Case 1: The problematic comma case
    text_comma = "Vehicle No./Wagon NO.: TN73BZ,7347"
    print(f"\nTesting Comma Case: '{text_comma}'")
    res = extract_vehicle(text_comma)
    print(f"Result: {res}")
    
    # Test Case 2: Misspelled label
    text_misspelled = "Vechile No: TN73BZ7347"
    print(f"\nTesting Misspelled Case: '{text_misspelled}'")
    res2 = extract_vehicle(text_misspelled)
    print(f"Result: {res2}")
    
    # Test Case 3: Wagon label
    text_wagon = "Wagon NO : KA01 AB 1234"
    print(f"\nTesting Wagon Case: '{text_wagon}'")
    res3 = extract_vehicle(text_wagon)
    print(f"Result: {res3}")

if __name__ == "__main__":
    test_extraction()
