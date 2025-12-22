import fitz, os

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
print("PDFKSS ANALYSIS")
print("=" * 60)

doc = fitz.open(pdfkss)
page = doc[0]

# TEXT LAYER
text = page.get_text()
print(f"1. TEXT LAYER: {len(text)} chars")
print(f"   Has text: {'YES' if len(text) > 100 else 'NO'}")

if len(text) > 100:
    print("\n   CRITICAL: PDFKSS HAS TEXT LAYER!")
    print("   This is why it's fast - NO OCR NEEDED")
    print(f"\n   Sample text:")
    print(f"   {text[:200]}")

# FONTS
fonts = page.get_fonts()
print(f"\n2. FONTS: {len(fonts)}")
if fonts:
    print(f"   Fonts present = TEXT LAYER EXISTS")

# IMAGES
images = page.get_images()
print(f"\n3. IMAGES: {len(images)}")
if images:
    img = doc.extract_image(images[0][0])
    print(f"   Size: {img['width']}x{img['height']} = {img['width']*img['height']:,} pixels")

# FILE
print(f"\n4. FILE SIZE: {os.path.getsize(pdfkss)//1024} KB")

doc.close()
print("\n" + "="*60)
