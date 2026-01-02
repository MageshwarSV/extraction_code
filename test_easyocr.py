# Test EasyOCR on page 17 crop
import easyocr
import re

save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"

print("Testing EasyOCR on page 17")
print("=" * 60)

reader = easyocr.Reader(['en'], gpu=False, verbose=False)

# Try the fixed crop
result = reader.readtext(f"{save_dir}\\page17_gc_fixed.png")
print("EasyOCR on fixed crop:")
for detection in result:
    bbox, text, conf = detection
    print(f"  '{text}' (conf: {conf:.2f})")
    # Extract digits
    digits = re.sub(r'\D', '', text)
    if len(digits) >= 4:
        print(f"  -> Digits: {digits}")

# Also try page 17_gc.png (the old crop)
print("\nEasyOCR on original page17_gc.png:")
result = reader.readtext(f"{save_dir}\\page17_gc.png")
for detection in result:
    bbox, text, conf = detection
    print(f"  '{text}' (conf: {conf:.2f})")

print("\n" + "=" * 60)
