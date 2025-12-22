#!/usr/bin/env python3
"""
Comprehensive fix for client1_format1.py
Restores the complete missing OCR loop section
"""

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

print("Reading file...")
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line numbers for insertion
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'if use_ocr:' in line and '_step_start = _time.time()' in lines[i+1] if i+1 < len(lines) else False:
        start_idx = i + 1  # Insert after the _step_start line
    if '# EXTRACT FIELDS' in line or 'Extracting fields from OCR text' in line:
        end_idx = i
        break

if start_idx is None or end_idx is None:
    print(f"ERROR: Could not locate insertion points")
    print(f"start_idx: {start_idx}, end_idx: {end_idx}")
    exit(1)

print(f"Found insertion point: lines {start_idx} to {end_idx}")

# The complete OCR section to insert
ocr_code = '''        logger.info("=" * 60)
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
                    text_len = len(page.get_text().strip())
                    if len(images) >= 1 and len(fonts) == 0 and text_len < 100:
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
            
            # OPTIMIZATION: Use simplified preprocessing for captured images
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

    # ============================================
'''

# Build new content
new_lines = lines[:start_idx] + [ocr_code] + lines[end_idx:]

# Write fixed file
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Fixed client1_format1.py!")
print("   - Restored OCR rendering section")
print("   - Added captured image detection")
print("   - Added OCR loop with optimization")
print("   - Captured images: 2 OCR runs (was 21)")
print("   - Regular PDFs: 21 OCR runs (unchanged)")
