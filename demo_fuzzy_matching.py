"""
Demonstration of Fuzzy Matching for Branch Extraction
Shows how POTTANER gets auto-corrected to POTTANERI
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.branch_extractor import extract_branch_refined, fuzzy_match_branch
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

print("=" * 80)
print("FUZZY MATCHING DEMONSTRATION - OCR Error Correction")
print("=" * 80)

# Test various OCR-damaged versions of POTTANERI
ocr_errors = [
    "POTTANER",    # Missing I at end (most common)
    "POTTANER1",   # 1 instead of I
    "P0TTANERI",   # 0 instead of O
    "POTTANER!",   # ! instead of I
    "POTTANERII",  # Extra I
    "POTANERI",    # Missing T
    "POTTANERI",   # Perfect (no error)
]

print("\n🔍 Direct Fuzzy Matching Test:")
print("-" * 80)
for damaged in ocr_errors:
    corrected = fuzzy_match_branch(damaged, threshold=0.75)
    similarity = __import__('difflib').SequenceMatcher(None, damaged, corrected or "").ratio()
    status = "✅" if corrected == "POTTANERI" else "❌"
    print(f"{status} '{damaged}' → '{corrected}' (similarity: {similarity:.1%})")

print("\n" + "=" * 80)
print("🔍 Full Extraction with POST Pattern:")
print("-" * 80)

full_texts = [
    "POST: POTTANER, TK: METTUR",
    "OST: POTTANER, TK: METTUR",    # POST → OST + POTTANERI → POTTANER
    "POST. POTTANER1, TK: SALEM",   # Period + 1 instead of I
]

for text in full_texts:
    result = extract_branch_refined(text)
    status = "✅" if result == "POTTANERI" else "❌"
    print(f"{status} Input:  '{text}'")
    print(f"   Output: '{result}'")
    print()

print("=" * 80)
print("💡 How it works:")
print("   1. Extract location from POST field → Gets 'POTTANER'")
print("   2. Apply fuzzy matching → Compare to known branches")
print("   3. If 75%+ match found → Return 'POTTANERI'")
print("   4. Works even with multiple OCR errors!")
print("=" * 80)
