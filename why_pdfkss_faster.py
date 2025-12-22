# why_pdfkss_faster.py
"""
WHY IS PDFKSS FASTER?
Find the specific difference that makes PDFKSS complete in 84s vs 102s for test PDF
"""
import fitz
import sys

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
testpdf = r'c:\Users\avin4\Desktop\boostentryai ui code\test\1e2563trufyqdgfwhdk.pdf'

print("="*70)
print("DETAILED COMPARISON: Why is PDFKSS faster?")
print("="*70)

def analyze(path, name):
    print(f"\n[{name}]")
    print("-"*70)
    
    doc = fitz.open(path)
    page = doc[0]
    
    # Text analysis
    text = page.get_text()
    print(f"Text layer chars: {len(text)}")
    
    # Image analysis
    images = page.get_images()
    print(f"Images: {len(images)}")
    
    if images:
        for i, img in enumerate(images):
            try:
                xref = img[0]
                base_img = doc.extract_image(xref)
                w = base_img.get('width', 0)
                h = base_img.get('height', 0)
                size_kb = len(base_img.get('image', b'')) // 1024
                fmt = base_img.get('ext', '?')
                total_pixels = w * h
                print(f"  Image {i+1}: {w}x{h} = {total_pixels:,} pixels, {size_kb}KB, {fmt}")
            except Exception as e:
                print(f"  Image {i+1}: Error - {e}")
    
    # Page size
    print(f"Page size: {page.rect.width:.1f} x {page.rect.height:.1f} pts")
    
    # Fonts
    fonts = page.get_fonts()
    print(f"Fonts: {len(fonts)}")
    
    # File size
    import os
    print(f"File size: {os.path.getsize(path)//1024}KB")
    
    doc.close()

analyze(pdfkss, "PDFKSS (84 seconds)")
analyze(testpdf, "Test PDF (102 seconds)")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)
print("\nKey differences to investigate:")
print("1. Image pixel count (more pixels = slower OCR)")
print("2. Image compression/format")
print("3. Text complexity")
print("4. Page dimensions")
print("\nThe PDF with FEWER pixels will OCR faster")
print("="*70)
