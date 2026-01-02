# Detailed OCR on GC candidates
from PIL import Image, ImageOps, ImageFilter
import pytesseract

save_dir = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c"

print("Detailed OCR on GC Candidates")
print("=" * 60)

for idx in [1, 2]:
    img = Image.open(f"{save_dir}\\gc_candidate_{idx}.png")
    print(f"\n=== Candidate {idx} ({img.size}) ===")
    
    for angle in [0, 90, 180, 270]:
        rot = img if angle == 0 else img.rotate(angle, expand=True)
        
        # Preprocessing
        gray = ImageOps.grayscale(rot)
        gray = ImageOps.autocontrast(gray)
        
        # Save preprocessed for inspection
        gray.save(f"{save_dir}\\gc_candidate_{idx}_rot{angle}_gray.png")
        
        # Try multiple PSM modes
        for psm in [6, 7, 8, 11, 13]:
            for char_filter in ['', '-c tessedit_char_whitelist=0123456789']:
                config = f'--psm {psm} {char_filter}'
                try:
                    text = pytesseract.image_to_string(gray, config=config, lang='eng')
                    text = text.strip().replace('\n', ' ')
                    if text:
                        print(f"  {angle} PSM{psm}: '{text}'")
                except:
                    pass

print("\n" + "=" * 60)
