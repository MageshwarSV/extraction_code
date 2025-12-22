# complete_pdfkss_forensics.py
"""
COMPLETE FORENSIC ANALYSIS OF PDFKSS
Find EVERY reason why it's fast (84 seconds)
"""
import fitz
import os
import sys

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'

print("="*70)
print("COMPLETE FORENSIC ANALYSIS: PDFKSS PDF")
print("="*70)

doc = fitz.open(pdfkss)
page = doc[0]

# 1. FILE LEVEL
print("\n[1] FILE PROPERTIES")
print("-"*70)
print(f"File size: {os.path.getsize(pdfkss)//1024} KB")
print(f"Pages: {len(doc)}")
print(f"PDF version: {doc.metadata.get('format', 'Unknown')}")
print(f"Encrypted: {doc.is_encrypted}")
print(f"Metadata: {doc.metadata}")

# 2. PAGE PROPERTIES
print("\n[2] PAGE PROPERTIES")
print("-"*70)
rect = page.rect
print(f"Page size: {rect.width:.1f} x {rect.height:.1f} pts")
print(f"Rotation: {page.rotation}")
print(f"CropBox: {page.cropbox}")
print(f"MediaBox: {page.mediabox}")

# 3. TEXT LAYER (CRITICAL!)
print("\n[3] TEXT LAYER ANALYSIS")
print("-"*70)
text = page.get_text()
print(f"Text chars: {len(text)}")
print(f"Has text layer: {'YES - FAST PATH' if len(text) > 100 else 'NO - SLOW PATH (OCR)'}")
if len(text) > 0:
    print(f"Sample (first 300 chars):")
    print(text[:300])
    print("...")

# 4. TEXT EXTRACTION METHODS
print("\n[4] TEXT EXTRACTION METHODS")
print("-"*70)
try:
    text_dict = page.get_text("dict")
    blocks = text_dict.get("blocks", [])
    text_blocks = [b for b in blocks if b.get("type") == 0]  # 0 = text
    image_blocks = [b for b in blocks if b.get("type") == 1]  # 1 = image
    print(f"Text blocks: {len(text_blocks)}")
    print(f"Image blocks: {len(image_blocks)}")
except Exception as e:
    print(f"dict extraction error: {e}")

# 5. FONTS (if fonts exist, text layer exists)
print("\n[5] FONT ANALYSIS")
print("-"*70)
fonts = page.get_fonts()
print(f"Fonts: {len(fonts)}")
if fonts:
    print("Font list (first 5):")
    for i, font in enumerate(fonts[:5]):
        print(f"  {i+1}. {font}")

# 6. IMAGES
print("\n[6] IMAGE ANALYSIS")
print("-"*70)
images = page.get_images()
print(f"Images: {len(images)}")
for i, img_info in enumerate(images):
    try:
        xref = img_info[0]
        base_img = doc.extract_image(xref)
        w = base_img.get('width', 0)
        h = base_img.get('height', 0)
        size_kb = len(base_img.get('image', b'')) // 1024
        fmt = base_img.get('ext', '?')
        colorspace = base_img.get('colorspace', 'Unknown')
        bpc = base_img.get('bpc', 'Unknown')  # bits per component
        
        print(f"  Image {i+1}:")
        print(f"    Size: {w}x{h} = {w*h:,} pixels")
        print(f"    File size: {size_kb} KB")
        print(f"    Format: {fmt}")
        print(f"    Colorspace: {colorspace}")
        print(f"    Bits/component: {bpc}")
    except Exception as e:
        print(f"  Image {i+1}: Error - {e}")

# 7. COMPRESSION
print("\n[7] COMPRESSION ANALYSIS")
print("-"*70)
try:
    xref_list = page.get_contents()
    if xref_list:
        for xref in xref_list:
            stream = doc.xref_stream(xref)
            if stream:
                print(f"Stream {xref}: {len(stream)} bytes")
                # Check for filters
                filters = doc.xref_get_key(xref, "Filter")
                print(f"  Filters: {filters}")
except Exception as e:
    print(f"Compression check error: {e}")

# 8. OBJECTS COUNT
print("\n[8] PDF OBJECTS")
print("-"*70)
print(f"Total objects: {doc.xref_length()}")

# 9. COMPARE WITH EXTRACTION PATH
print("\n[9] EXTRACTION PATH PREDICTION")
print("-"*70)
has_substantial_text = len(text.strip()) > 100
print(f"Text length: {len(text)}")
print(f"Will use: {'FAST PATH (text layer)' if has_substantial_text else 'SLOW PATH (OCR)'}")

# 10. SAVE STRUCTURE
print("\n[10] PDF STRUCTURE DUMP")
print("-"*70)
try:
    # Get first page structure
    page_dict = doc.xref_object(page.xref)
    print("Page object:")
    print(page_dict[:500] if len(page_dict) > 500 else page_dict)
except Exception as e:
    print(f"Structure dump error: {e}")

doc.close()

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print("\nKEY FINDINGS TO LOOK FOR:")
print("1. Does it have a text layer? (If YES = FAST, if NO = SLOW)")
print("2. Image pixel count (lower = faster OCR)")
print("3. Image compression/format")
print("4. Any special PDF flags or optimizations")
print("="*70)
