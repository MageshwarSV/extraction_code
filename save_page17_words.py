# Debug page 17 - save all words to file
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"

pages = convert_from_path(pdf_path, dpi=300, first_page=17, last_page=17)
page = pages[0]
rotated = page.rotate(90, expand=True)

top_height = int(rotated.height * 0.50)
top_region = rotated.crop((0, 0, rotated.width, top_height))

data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)

# Collect all words
all_words = []
for i, word in enumerate(data['text']):
    if word and len(word.strip()) > 0:
        all_words.append({
            'word': word,
            'x': data['left'][i],
            'y': data['top'][i],
            'w': data['width'][i]
        })

# Sort by X (rightmost first)
all_words.sort(key=lambda w: w['x'], reverse=True)

with open(f"{save_dir}\\page17_words.txt", 'w') as f:
    f.write("Page 17 - All words (rightmost first)\n")
    f.write("=" * 50 + "\n\n")
    
    for w in all_words[:50]:
        f.write(f"x={w['x']:4d} y={w['y']:4d}: '{w['word']}'\n")

print(f"Saved to: {save_dir}\\page17_words.txt")
