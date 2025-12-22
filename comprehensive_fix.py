#!/usr/bin/env python3
"""
Comprehensive fix for client1_format1.py
Rebuilds the corrupted OCR section with proper indentation and optimization
"""

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

print("Reading broken file...")
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find where OCR section should start and end
# Look for the text_layer_check logging line
marker_start = 'logger.info("[TIMING] Text layer check:'
marker_end = '# EXTRACT FIELDS (All except Delivery Address)'

if marker_start not in content or marker_end not in content:
    print("ERROR: Cannot find markers!")
    exit(1)

start_idx = content.find(marker_start)
# Find the end of this line
start_line_end = content.find('\n', start_idx)

end_idx = content.find(marker_end)

print(f"Found corruption between positions {start_idx} and {end_idx}")

# The complete, properly indented OCR section
ocr_section = '''
    # ============================================
    # SLOW PATH: Render PDF and Run Tesseract OCR (only if needed)
    # ============================================
    if use_ocr:
        _step_start = _time.time()
        logger.info("=" * 60)
        logger.info("PASS 1: Tesseract OCR @ DPI 300 (Slow path)")
        logger.info(f"DEBUG: poppler variable = {poppler_bin}")
        logger.info("=" * 60)
        
        try:
            from pdf2image import convert_from_path
            import fitz
            
            # Detect if this is a captured image PDF
            ocr_dpi = 300
            is_captured_image = False
            try:
                doc = fitz.open(pdf_path)
                if len(doc) == 1:
                    page = doc[0]
                    fonts = page.get_fonts()
                    images = page.get_images()
                    # FIXED: Just check images and fonts (no text_len check)
                    if len(images) >= 1 and len(fonts) == 0:
                        ocr_dpi = 200
                        is_captured_image = True
                        logger.info("Detected CAPTURED IMAGE - using DPI 200 + optimized preprocessing")
                doc.close()
            except:
                pass
            
            if poppler_bin:
                pages = convert_from_path(pdf_path, dpi=ocr_dpi, poppler_path=poppler_bin)
            else:
                pages = convert_from_path(pdf_path, dpi=ocr_dpi)
            logger.info("✓ Rendered %d page(s) from PDF", len(pages))
            _step_times['pdf_render'] = _time.time() - _step_start
            logger.info("[TIMING] PDF rendering: %.2fs", _step_times['pdf_render'])
        except Exception as e:
            if platform.system() == "Windows":
                raise RuntimeError(
                    f"Failed to render PDF: {e}\\n"
                    "Install Poppler for Windows and set POPPLER_PATH environment variable."
                )
            raise

        # Run OCR on all pages
        _ocr_start = _time.time()
        all_blocks: List[str] = []
        
        for pg_num, pg in enumerate(pages, 1):
            logger.info("  Processing page %d...", pg_num)
            originals.append(pg)
            
            # OPTIMIZATION: Pass is_captured_image to use 2 OCR runs instead of 21
            variants = _preprocess_variants_fast(pg, is_captured_image=is_captured_image)
            page_texts: List[str] = []
            
            for v in variants:
                page_texts.extend(_ocr_configs_fast(v, is_captured_image=is_captured_image))
            
            merged = _merge_text(page_texts) if page_texts else ""
            all_blocks.append(merged)

        # Combine all page text
        text = "\\n".join(all_blocks)
        _step_times['tesseract_ocr'] = _time.time() - _ocr_start
        logger.info("[TIMING] Tesseract OCR: %.2fs", _step_times['tesseract_ocr'])
        logger.info("✓ OCR completed. Total text length: %d characters", len(text))

    '''

# Rebuild the file
new_content = content[:start_line_end] + ocr_section + '\n    ' + content[end_idx:]

# Write fixed file
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ File fixed!")
print()
print("Applied optimizations:")
print("  1. Restored complete OCR loop")
print("  2. Fixed detection: removed text_len < 100 check")
print("  3. Added is_captured_image flag to preprocessing calls")
print()
print("Result: Captured images will use 2 OCR runs (vs 21)")
print()
print("Testing...")

# Verify syntax
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', filepath], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print("✅ Syntax check PASSED!")
    print("\nReady to test with: python test2_captured_only.py")
else:
    print("❌ Syntax check FAILED:")
    print(result.stderr)
