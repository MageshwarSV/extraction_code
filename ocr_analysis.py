# OCR Analysis on specific regions
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from PIL import Image, ImageOps
import pytesseract

save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("OCR Analysis on narrow/tall pink regions (likely G.C.No boxes)")
print("=" * 60)

# Test narrow regions (1, 3, 4 are narrow and tall)
for region_num in [1, 3, 4]:
    img = Image.open(f"{save_dir}\\page3_region{region_num}.png")
    
    print(f"\n=== Region {region_num} ({img.size[0]}x{img.size[1]}) ===")
    
    # Try all 4 rotations with digit-only OCR
    for angle in [0, 90, 180, 270]:
        if angle == 0:
            rotated = img
        else:
            rotated = img.rotate(angle, expand=True)
        
        # Save rotated version for inspection
        rotated.save(f"{save_dir}\\page3_region{region_num}_rot{angle}.png")
        
        # OCR with digit whitelist
        config = '--psm 6 -c tessedit_char_whitelist=0123456789GCNo.:'
        text = pytesseract.image_to_string(rotated, config=config, lang='eng')
        text = text.strip().replace('\n', ' ')
        
        if text:
            print(f"  {angle}: {text}")
        
        # Also try PSM 7 (single text line)
        config2 = '--psm 7 -c tessedit_char_whitelist=0123456789'
        text2 = pytesseract.image_to_string(rotated, config=config2, lang='eng')
        text2 = text2.strip()
        if text2 and text2 != text:
            print(f"  {angle} (PSM7): {text2}")

print("\n" + "=" * 60)
print("Check page3_region*_rot*.png files to see rotations")
