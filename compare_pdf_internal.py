# compare_pdf_internal.py
"""
Compare internal structure of pdfkss PDF vs captured image PDF
to understand why one OCRs faster than the other.
"""
import os
import fitz
from PIL import Image
import io

pdfkss_file = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
test_file = r'c:\Users\avin4\Desktop\boostentryai ui code\test\test1.pdf'

def analyze_pdf(path, name):
    print(f"\n{'='*60}")
    print(f"ANALYZING: {name}")
    print(f"Path: {path}")
    print(f"{'='*60}")
    
    size_kb = os.path.getsize(path) // 1024
    print(f"File Size: {size_kb} KB")
    
    doc = fitz.open(path)
    print(f"Pages: {len(doc)}")
    
    page = doc[0]
    print(f"Page Size: {page.rect.width} x {page.rect.height} pts")
    
    # Check text layer
    text = page.get_text().strip()
    print(f"Text Layer: {len(text)} chars")
    
    # Check images embedded
    images = page.get_images()
    print(f"Embedded Images: {len(images)}")
    
    for i, img in enumerate(images[:3]):
        xref = img[0]
        try:
            base_img = doc.extract_image(xref)
            if base_img:
                print(f"  Image {i+1}: {base_img.get('width', 0)}x{base_img.get('height', 0)}, {base_img.get('ext', '?')}, {len(base_img.get('image', b''))//1024}KB")
        except:
            pass
    
    # Render page and check size
    pix = page.get_pixmap(dpi=300)
    print(f"Rendered at DPI 300: {pix.width}x{pix.height} pixels")
    
    # Check if PDF has fonts (vector text)
    fonts = page.get_fonts()
    print(f"Fonts (vector text): {len(fonts)}")
    
    doc.close()

# Analyze both
analyze_pdf(pdfkss_file, "PDFKSS (Fast)")
analyze_pdf(test_file, "TEST/Captured (Slow)")
