#!/usr/bin/env python3
"""
Fix captured image detection - make it more robust

Current problem: Detection fails because uploaded PDFs have fonts
Solution: Check multiple signals, not just fonts
"""

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

print("Fixing captured image detection...")

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the detection logic
old_detection = '''            # Detect if this is a captured image PDF
            ocr_dpi = 300
            is_captured_image = False
            try:
                doc = fitz.open(pdf_path)
                if len(doc) == 1:
                    page = doc[0]
                    fonts = page.get_fonts()
                    images = page.get_images()
                    # Captured images have: 1 page, 1+ images, 0 fonts
                    if len(images) >= 1 and len(fonts) == 0:
                        ocr_dpi = 200
                        is_captured_image = True
                        logger.info("Detected CAPTURED IMAGE - using DPI 200 + optimized preprocessing")
                doc.close()
            except:
                pass'''

new_detection = '''            # Detect if this is a captured image PDF (ROBUST DETECTION)
            ocr_dpi = 300
            is_captured_image = False
            try:
                doc = fitz.open(pdf_path)
                if len(doc) == 1:
                    page = doc[0]
                    fonts = page.get_fonts()
                    images = page.get_images()
                    text_len = len(page.get_text().strip())
                    
                    # Multiple detection signals for captured images:
                    # 1. Has images but minimal/no text layer (< 500 chars)
                    # 2. Has images and few/no fonts (< 3)
                    # 3. PDF creator is "ReportLab" (from upload_routes.py)
                    # 4. Single page with single large image
                    
                    has_minimal_text = text_len < 500
                    has_few_fonts = len(fonts) < 3
                    has_images = len(images) >= 1
                    
                    # Check PDF metadata for ReportLab (upload_routes.py creates these)
                    producer = doc.metadata.get('producer', '').lower()
                    creator = doc.metadata.get('creator', '').lower()
                    is_from_upload = 'reportlab' in producer or 'reportlab' in creator
                    
                    # Captured image if:
                    # - Has images AND (few fonts OR minimal text OR from upload)
                    if has_images and (has_few_fonts or has_minimal_text or is_from_upload):
                        ocr_dpi = 200
                        is_captured_image = True
                        logger.info("Detected CAPTURED IMAGE - using DPI 200 + optimized preprocessing")
                        logger.info(f"  Detection: images={len(images)}, fonts={len(fonts)}, text={text_len} chars, from_upload={is_from_upload}")
                
                doc.close()
            except Exception as e:
                logger.debug(f"Detection failed: {e}")
                pass'''

if old_detection in content:
    content = content.replace(old_detection, new_detection)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Updated detection logic!")
    print("\nNew detection checks:")
    print("  1. Has images AND few fonts (< 3)")
    print("  2. OR has images AND minimal text (< 500 chars)")
    print("  3. OR has images AND created by ReportLab (uploaded)")
    print("\nThis should catch ALL captured images!")
else:
    print("❌ Could not find detection code to replace")
    exit(1)

# Verify syntax
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', filepath], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print("\n✅ Syntax check PASSED!")
else:
    print("\n❌ Syntax error:")
    print(result.stderr)
