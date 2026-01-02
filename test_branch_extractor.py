"""
Test branch extractor with actual Format 3 document
"""
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.branch_extractor import extract_branch_refined
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# Load actual OCR text from Format 3 document
with open(r'c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_ocr_text.txt', 'r', encoding='utf-8') as f:
    actual_text = f.read()

print("=" * 80)
print("TESTING WITH ACTUAL FORMAT 3 DOCUMENT")
print("=" * 80)

print("\nDocument Preview (first 500 chars):")
print("-" * 80)
print(actual_text[:500])
print("-" * 80)

print("\n🔍 Extracting Branch/Source from POST field...")
branch = extract_branch_refined(actual_text)

print("\n" + "=" * 80)
if branch:
    print(f"✅ SUCCESS: Extracted Branch = '{branch}'")
else:
    print("❌ FAILED: Could not extract branch")
    print("\nSearching for POST pattern in text...")
    for i, line in enumerate(actual_text.split('\n'), 1):
        if 'POST' in line.upper() or 'POTT' in line.upper():
            print(f"  Line {i}: {line}")

print("=" * 80)
