# Test EasyOCR on all crops - save to file
import easyocr
import re
import os

save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"
output_file = f"{save_dir}\\easyocr_results.txt"

reader = easyocr.Reader(['en'], gpu=False, verbose=False)

with open(output_file, 'w') as f:
    f.write("EasyOCR Results on All GC Crops\n")
    f.write("=" * 50 + "\n\n")
    
    for filename in sorted(os.listdir(save_dir)):
        if filename.endswith('.png') and 'page' in filename:
            filepath = os.path.join(save_dir, filename)
            f.write(f"{filename}:\n")
            
            result = reader.readtext(filepath)
            for detection in result:
                bbox, text, conf = detection
                f.write(f"  '{text}' (conf: {conf:.2f})\n")
                
                digits = re.sub(r'\D', '', text)
                if len(digits) >= 4:
                    f.write(f"  -> GC Number: {digits}\n")
            
            if not result:
                f.write("  No text detected\n")
            f.write("\n")

print(f"Results saved to: {output_file}")
