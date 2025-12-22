# compare_pdf_internal2.py
import os
import fitz

pdfkss_file = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
test_file = r'c:\Users\avin4\Desktop\boostentryai ui code\test\test1.pdf'

def analyze(path, name):
    print(f"\n{name}:")
    doc = fitz.open(path)
    page = doc[0]
    print(f"  File Size: {os.path.getsize(path)//1024}KB")
    print(f"  Text Layer: {len(page.get_text().strip())} chars")
    print(f"  Fonts: {len(page.get_fonts())}")
    print(f"  Images: {len(page.get_images())}")
    for img in page.get_images()[:1]:
        try:
            bi = doc.extract_image(img[0])
            print(f"  Image Size: {bi.get('width')}x{bi.get('height')}")
        except:
            pass
    pix = page.get_pixmap(dpi=300)
    print(f"  Rendered: {pix.width}x{pix.height} pixels")
    doc.close()

analyze(pdfkss_file, "PDFKSS (Fast)")
analyze(test_file, "TEST (Slow)")
