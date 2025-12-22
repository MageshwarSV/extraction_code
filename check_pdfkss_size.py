import fitz
doc = fitz.open(r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf')
images = doc[0].get_images()
if images:
    img_data = doc.extract_image(images[0][0])
    print(f"PDFKSS image: {img_data['width']}x{img_data['height']}")
    print(f"Total pixels: {img_data['width'] * img_data['height']:,}")
    print(f"Max dimension: {max(img_data['width'], img_data['height'])}")
doc.close()
