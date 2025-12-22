#!/usr/bin/env python3
"""
Show what's in the test PDF (optimized_test.pdf)
Convert first page to image so you can see the quality
"""

import fitz
from PIL import Image
import io

pdf_path = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*80)
print("ANALYZING TEST PDF: optimized_test.pdf")
print("="*80)

doc = fitz.open(pdf_path)

print(f"\nPDF Info:")
print(f"  Pages: {len(doc)}")
print(f"  Creator: {doc.metadata.get('creator', 'N/A')}")
print(f"  Producer: {doc.metadata.get('producer', 'N/A')}")
print(f"  Format: {doc.metadata.get('format', 'N/A')}")

page = doc[0]
print(f"\nPage 1:")
print(f"  Size: {page.rect.width} x {page.rect.height}")
print(f"  Fonts: {len(page.get_fonts())}")
print(f"  Images: {len(page.get_images())}")
print(f"  Text length: {len(page.get_text().strip())}")

# Extract image
if page.get_images():
    xref = page.get_images()[0][0]
    base_image = doc.extract_image(xref)
    img = Image.open(io.BytesIO(base_image['image']))
    
    print(f"\nImage in PDF:")
    print(f"  Size: {img.size[0]} x {img.size[1]} pixels")
    print(f"  Mode: {img.mode}")
    print(f"  Format: {base_image.get('ext', 'unknown')}")
    print(f"  File size: {len(base_image['image']):,} bytes")
    
    # Save for viewing
    img.save('test_pdf_image.jpg', 'JPEG', quality=95)
    print(f"\n✓ Saved image as: test_pdf_image.jpg")
    
    # Also render the PDF page
    pix = page.get_pixmap(dpi=150)
    pix.save('test_pdf_page_rendered.png')
    print(f"✓ Saved rendered page as: test_pdf_page_rendered.png")

doc.close()

print("\n" + "="*80)
print("FILES CREATED:")
print("="*80)
print("\n1. test_pdf_image.jpg - The raw image from the PDF")
print("2. test_pdf_page_rendered.png - How the PDF page looks when rendered")
print("\nOpen these files to see the quality!")
