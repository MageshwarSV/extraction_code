"""
Test: Run the SAME extraction code on both OCR texts
This will prove that the code produces different results based on input text
"""

import re
import sys
sys.path.insert(0, '.')

# Load both OCR texts
with open('ocr_raw_local.txt', 'r', encoding='utf-8') as f:
    local_text = f.read()

with open('ocr_raw_docker.txt', 'r', encoding='utf-8') as f:
    docker_text = f.read()

def extract_eway_bill_test(text, label):
    """
    Simplified version of the extraction logic from client1_format1.py
    """
    print(f"\n{'='*60}")
    print(f"TESTING: {label}")
    print(f"{'='*60}")
    print(f"Text length: {len(text)} chars")
    
    # Strategy 1: Direct 12-digit pattern (should work for both)
    all_12digit = re.findall(r'\b(\d{12})\b', text)
    print(f"\nStrategy 1 - Direct \\b(\\d{12})\\b pattern:")
    print(f"  Found: {all_12digit}")
    
    # Strategy 2: Line-by-line with EWB keyword
    print(f"\nStrategy 2 - Line-by-line with EWB keyword:")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r'(?:E-?Way|EWB|EWE)', line, re.IGNORECASE):
            print(f"  Line {i}: {line[:80]}...")
            
            # Same line exact match
            same_line_match = re.search(r'\b([0-9]{12})\b', line)
            if same_line_match:
                print(f"    -> Same line exact 12-digit: {same_line_match.group(1)}")
                
            # Cleaned line approach (THIS IS THE PROBLEM!)
            cleaned_line = re.sub(r'[^0-9]', '', line)
            print(f"    -> Cleaned (digits only): {cleaned_line}")
            print(f"    -> Cleaned length: {len(cleaned_line)}")
            
            if len(cleaned_line) >= 12:
                # Take first 12 digits - THIS IS WHERE THE BUG HAPPENS
                first_12 = cleaned_line[:12]
                print(f"    -> First 12 digits: {first_12}")
    
    # What does the extraction return?
    # Use direct pattern if available (most reliable)
    if all_12digit:
        return all_12digit[0]
    return None

# Run on both
local_result = extract_eway_bill_test(local_text, "LOCAL (Windows)")
docker_result = extract_eway_bill_test(docker_text, "DOCKER (Linux)")

print(f"\n{'='*60}")
print("FINAL RESULTS:")
print(f"{'='*60}")
print(f"Local extraction:  {local_result}")
print(f"Docker extraction: {docker_result}")

if local_result == docker_result:
    print("\n✓ SAME RESULT - Both extractions match!")
else:
    print("\n✗ DIFFERENT RESULTS - This proves the OCR text difference causes the issue!")
