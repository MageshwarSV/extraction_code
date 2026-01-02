import cv2
import pytesseract
import os

# Path to the debug image created by the previous script
img_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_final_rot180.png"

if not os.path.exists(img_path):
    print(f"File not found: {img_path}")
    # Try the raw one
    img_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_gc_failed_final_rot180.png"

if not os.path.exists(img_path):
    print("No debug images found to test.")
    exit()

print(f"Testing Tesseract on: {os.path.basename(img_path)}")
img = cv2.imread(img_path)

configs = [
    ('--psm 7', "Single Line"),
    ('--psm 6', "Uniform Block"),
    ('--psm 3', "Auto Segmentation"),
    ('--psm 13', "Raw Line"),
    ('--psm 6 -c tessedit_char_whitelist=0123456789', "Block + Whitelist"),
    ('--psm 7 -c tessedit_char_whitelist=0123456789', "Line + Whitelist"),
]

print("-" * 60)
for conf, desc in configs:
    try:
        text = pytesseract.image_to_string(img, config=conf).strip()
        print(f"Config: {conf:<45} | Text: '{text}'")
    except Exception as e:
        print(f"Config: {conf:<45} | Error: {e}")
print("-" * 60)

# Also try scaling it before reading
print("\n--- Testing Scaled Versions ---")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

for scale in [2, 3, 4]:
    scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    text = pytesseract.image_to_string(scaled, config='--psm 6').strip()
    print(f"Scale {scale}x + PSM 6: '{text}'")
