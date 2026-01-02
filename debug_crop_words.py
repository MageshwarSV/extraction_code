
import cv2
import pytesseract
import sys
import os

# Explicitly use the generated crop
crop_path = r"c:\Users\avin4\.gemini\antigravity\brain\e4213f35-d609-471b-894b-bd215ca08950\page_1_delivery_robust.png"

def analyze_crop():
    if not os.path.exists(crop_path):
        print("Crop not found.")
        return

    print(f"Analyzing: {crop_path}")
    img = cv2.imread(crop_path)
    
    # Standardize preprocessing same as the function
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    data = pytesseract.image_to_data(thresh, config='--psm 6', output_type=pytesseract.Output.DICT)
    
    output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\debug_words.txt"
    with open(output_file, 'w') as f:
        f.write("-" * 20 + "\n")
        f.write("DETECTED WORDS:\n")
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if text:
                f.write(f"Word: '{text}' | Top: {data['top'][i]} | Conf: {data['conf'][i]}\n")
    print(f"Output written to {output_file}")
            
if __name__ == "__main__":
    analyze_crop()
