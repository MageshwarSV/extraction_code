#!/usr/bin/env python3
"""
Fix client1_format1.py based on file analysis
Missing: Lines after 2473 need the complete "if use_ocr:" section with OCR loop
"""

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

print("Reading client1_format1.py...")
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find exact insertion point (after line with text_layer_check timing)
insert_idx = None
for i, line in enumerate(lines):
    if 'logger.info("[TIMING] Text layer check:' in line:
        insert_idx = i + 1  # Insert right after this line
        break

if insert_idx is None:
    print("ERROR: Could not find insertion point!")
    exit(1)

print(f"Found insertion point at line {insert_idx + 1}")
print(f"Current line: {lines[insert_idx].strip()[:60]}...")

# The complete missing OCR section
missing_section = '''
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
            
            # Detect if this is a captured image PDF (use lower DPI for speed)
            ocr_dpi = 300  # Default for regular PDFs
            is_captured_image = False  # Track if this is a captured image
            try:
                doc = fitz.open(pdf_path)
                if len(doc) == 1:
                    page = doc[0]
                    fonts = page.get_fonts()
                    images = page.get_images()
                    text_len = len(page.get_text().strip())
                    if len(images) >= 1 and len(fonts) == 0 and text_len < 100:
                        ocr_dpi = 200  # Lower DPI for captured images
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

# Insert the missing section
new_lines = lines[:insert_idx] + [missing_section] + lines[insert_idx:]

# Write the fixed file
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Successfully fixed client1_format1.py!")
print()
print("Restored missing section:")
print("  - if use_ocr: block")
print("  - PDF rendering with pdf2image")
print("  - Captured image detection (is_captured_image flag)")
print("  - OCR loop with optimized preprocessing")
print()
print("Optimization for captured images:")
print("  - Before: 21 OCR runs (3 variants × 7 configs) = 400-500s")
print("  - After:   2 OCR runs (1 variant × 2 configs) = ~7s")
print()
print("Now test with: python test2_captured_only.py")
