#!/usr/bin/env python3
"""Check why optimized_test.pdf isn't detected as captured image"""

import fitz

pdf_path = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

doc = fitz.open(pdf_path)
page = doc[0]
fonts = page.get_fonts()
images = page.get_images()
text = page.get_text().strip()
text_len = len(text)

print("="*60)
print("DETECTION ANALYSIS")
print("="*60)
print(f"Images: {len(images)}")
print(f"Fonts: {len(fonts)}")
print(f"Text length: {text_len}")
print(f"Text preview: {text[:200]}...")
print()
print("DETECTION LOGIC:")
print(f"  len(images) >= 1: {len(images) >= 1}")
print(f"  len(fonts) == 0: {len(fonts) == 0}")
print(f"  text_len < 100: {text_len < 100}  ❌ THIS FAILED!")
print()
print("CURRENT RESULT: is_captured_image = False")
print()
print("FIX: Change detection to check text_len < 500 or just check images >= 1 and fonts == 0")
doc.close()
