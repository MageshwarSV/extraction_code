# Crop page 17 using fixed position (similar to other pages)
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"

print("Fixing Page 17 crop")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=300, first_page=17, last_page=17)
page = pages[0]
rotated = page.rotate(90, expand=True)

print(f"Rotated image size: {rotated.size}")

# Based on other pages, G.C.No is typically at:
# X: around 2500-2700
# Y: around 500-700
# Let's crop a fixed region where G.C.No should be

# Use approximate position based on successful pages
# Page 1: (2575, 629), Page 9: (2551, 648), Page 12: (2520, 646)
# Average: x~2550, y~640

crop_x1 = 2500
crop_y1 = 550
crop_x2 = 3100  # Wide enough for number
crop_y2 = 800

crop = rotated.crop((crop_x1, crop_y1, crop_x2, crop_y2))
crop.save(f"{save_dir}\\page17_gc_fixed.png")
print(f"Saved fixed crop: {crop.size}")

# Also try EasyOCR on this crop
try:
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False)
    result = reader.readtext(f"{save_dir}\\page17_gc_fixed.png")
    print("\nEasyOCR results:")
    for detection in result:
        text = detection[1]
        conf = detection[2]
        print(f"  '{text}' (conf: {conf:.2f})")
except Exception as e:
    print(f"EasyOCR error: {e}")

# Also try Tesseract on the fixed crop
text = pytesseract.image_to_string(crop, config='--psm 6', lang='eng')
print(f"\nTesseract OCR: {text.strip()[:50]}")

print("=" * 60)
