# compare_no_textlayer.py
"""
Remove text layer from BOTH PDFs and compare extraction timing.
This tests the pure OCR path for both files.
"""
import os, sys, time, fitz
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

pdfkss_file = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
test_file = r'c:\Users\avin4\Desktop\boostentryai ui code\test\1234yyy.pdf'

def remove_text_layer(src_path, dst_path):
    """Remove text layer by converting PDF to pure image"""
    doc = fitz.open(src_path)
    new_doc = fitz.open()
    
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
        new_page.insert_image(img_rect, pixmap=pix)
    
    new_doc.save(dst_path)
    new_doc.close()
    doc.close()

def analyze_pdf(path):
    """Analyze PDF properties"""
    doc = fitz.open(path)
    page = doc[0]
    
    info = {
        'size_kb': os.path.getsize(path) // 1024,
        'width': page.rect.width,
        'height': page.rect.height,
        'text_chars': len(page.get_text().strip()),
        'fonts': len(page.get_fonts()),
        'images': len(page.get_images()),
    }
    
    # Get embedded image size
    images = page.get_images()
    if images:
        try:
            base_img = doc.extract_image(images[0][0])
            info['img_width'] = base_img.get('width', 0)
            info['img_height'] = base_img.get('height', 0)
            info['img_size_kb'] = len(base_img.get('image', b'')) // 1024
        except:
            pass
    
    doc.close()
    return info

def run_extraction(path):
    """Run extraction and return time"""
    from engine.extractors.client1_format1 import run
    start = time.time()
    result = run(path)
    elapsed = time.time() - start
    return elapsed, result

print("=" * 70)
print("COMPARISON: PDFKSS vs TEST (BOTH WITHOUT TEXT LAYER)")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)

# Step 1: Create versions without text layer
print("\n[STEP 1] REMOVING TEXT LAYERS...")
pdfkss_no_text = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\pdfkss_no_textlayer.pdf'
test_no_text = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\1234yyy_no_textlayer.pdf'

print(f"  Converting pdfkss...")
remove_text_layer(pdfkss_file, pdfkss_no_text)
print(f"  Converting 1234yyy.pdf...")
remove_text_layer(test_file, test_no_text)
print("  DONE")

# Step 2: Analyze both
print("\n[STEP 2] PDF PROPERTIES (WITHOUT TEXT LAYER):")
print("-" * 70)

info1 = analyze_pdf(pdfkss_no_text)
info2 = analyze_pdf(test_no_text)

print(f"{'Property':<25} {'PDFKSS':<20} {'1234yyy.pdf':<20}")
print("-" * 70)
print(f"{'File Size (KB)':<25} {info1['size_kb']:<20} {info2['size_kb']:<20}")
print(f"{'Page Width (pts)':<25} {info1['width']:<20} {info2['width']:<20}")
print(f"{'Page Height (pts)':<25} {info1['height']:<20} {info2['height']:<20}")
print(f"{'Text Chars':<25} {info1['text_chars']:<20} {info2['text_chars']:<20}")
print(f"{'Fonts':<25} {info1['fonts']:<20} {info2['fonts']:<20}")
print(f"{'Images':<25} {info1['images']:<20} {info2['images']:<20}")
if 'img_width' in info1:
    print(f"{'Image Width':<25} {info1.get('img_width',0):<20} {info2.get('img_width',0):<20}")
    print(f"{'Image Height':<25} {info1.get('img_height',0):<20} {info2.get('img_height',0):<20}")
    print(f"{'Image Size (KB)':<25} {info1.get('img_size_kb',0):<20} {info2.get('img_size_kb',0):<20}")

# Step 3: Run extraction on both
print("\n[STEP 3] EXTRACTION TIMING:")
print("-" * 70)

print(f"\nPDFKSS (no text layer):")
print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")
t1, r1 = run_extraction(pdfkss_no_text)
print(f"  End: {datetime.now().strftime('%H:%M:%S')}")
print(f"  TIME: {t1:.1f} seconds ({t1/60:.1f} min)")
print(f"  Invoice: {r1.get('Invoice No', 'N/A')}")

print(f"\n1234yyy.pdf (no text layer):")
print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")
t2, r2 = run_extraction(test_no_text)
print(f"  End: {datetime.now().strftime('%H:%M:%S')}")
print(f"  TIME: {t2:.1f} seconds ({t2/60:.1f} min)")
print(f"  Invoice: {r2.get('Invoice No', 'N/A')}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"PDFKSS Time: {t1:.1f} seconds ({t1/60:.1f} min)")
print(f"1234yyy Time: {t2:.1f} seconds ({t2/60:.1f} min)")
print(f"DIFFERENCE: {abs(t2-t1):.1f} seconds")
print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")
