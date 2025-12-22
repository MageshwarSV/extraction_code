# add_detailed_logging.py
"""
Add detailed logging to client1_format1.py to track execution steps
"""

filepath = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\engine\extractors\client1_format1.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add timing logger at the top of run() function
import_section = '''import logging
logger = logging.getLogger(__name__)
'''

if 'import logging' not in content:
    # Add after existing imports
    content = content.replace('from typing import', 'import logging\nimport time as timing_module\nfrom typing import', 1)

# Create logged version with timing
logged_content = content

# Add detailed logging points
logging_insertions = [
    # At start of run()
    ('def run(', '''def run(
    # DETAILED LOGGING ENABLED
    import time as timing_module
    _step_times = {}
    _start_time = timing_module.time()
    logger.info("="*70)
    logger.info("EXTRACTION START: %s", pdf_path)
    logger.info("="*70)
    
'''),
    
    # Before FAST PATH check
    ('logger.info("Attempting FAST PATH:', '''_step_start = timing_module.time()
    logger.info("Attempting FAST PATH:'''),
    
    # After FAST PATH result
    ('if text_layer_text:', '''_step_times['fast_path_check'] = timing_module.time() - _step_start
    logger.info("FAST PATH check took: %.2fs", _step_times['fast_path_check'])
    if text_layer_text:'''),
    
    # Before OCR rendering
    ('logger.info("PASS 1: Tesseract OCR', '''_step_start = timing_module.time()
        logger.info("PASS 1: Tesseract OCR'''),
    
    # After rendering
    ('logger.info("✓ Rendered %d page', '''_step_times['pdf_render'] = timing_module.time() - _step_start
        logger.info("PDF rendering took: %.2fs", _step_times['pdf_render'])
        logger.info("✓ Rendered %d page'''),
    
    # Before OCR processing
    ('for pg_num, pg in enumerate(pages, 1):', '''_ocr_start = timing_module.time()
        for pg_num, pg in enumerate(pages, 1):'''),
    
    # After OCR complete
    ('logger.info("✓ OCR completed.', '''_step_times['tesseract_ocr'] = timing_module.time() - _ocr_start
        logger.info("Tesseract OCR took: %.2fs", _step_times['tesseract_ocr'])
        logger.info("✓ OCR completed.'''),
]

# Apply logging insertions
for old_text, new_text in logging_insertions:
    if old_text in logged_content:
        logged_content = logged_content.replace(old_text, new_text, 1)

# Add final summary logging before return
logged_content = logged_content.replace(
    'return raw_data',
    '''_total_time = timing_module.time() - _start_time
    logger.info("="*70)
    logger.info("EXTRACTION COMPLETE: %.2fs total", _total_time)
    logger.info("Step breakdown:")
    for step, duration in _step_times.items():
        logger.info("  %s: %.2fs (%.1f%%)", step, duration, (duration/_total_time)*100)
    logger.info("="*70)
    return raw_data''',
    1
)

# Save logged version
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(logged_content)

print("✓ Added detailed logging to client1_format1.py")
print("  - Timing for each major step")
print("  - Total extraction time")
print("  - Percentage breakdown")
