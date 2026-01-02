# Fix page 17 - show ALL words in top 50% to find the label
import sys
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import re

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
save_dir = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify"

print("Debug Page 17 - Show all words in right area")
print("=" * 60)

pages = convert_from_path(pdf_path, dpi=300, first_page=17, last_page=17)
page = pages[0]
rotated = page.rotate(90, expand=True)

# Top 50%
top_height = int(rotated.height * 0.50)
top_region = rotated.crop((0, 0, rotated.width, top_height))

data = pytesseract.image_to_data(top_region, config='--psm 6', lang='eng', output_type=Output.DICT)

# Show all words in the right area (x > 2400) where G.C.No should be
print("Words in right area (x > 2400, y 500-800):")
for i, word in enumerate(data['text']):
    if not word:
        continue
    x = data['left'][i]
    y = data['top'][i]
    
    if x > 2400 and 500 < y < 800:
        print(f"  '{word}' at ({x}, {y})")

print("\n" + "=" * 60)

# Try to find G.C.No by looking for consecutive words that form the pattern
print("\nLooking for G + C + No pattern (consecutive words):")
words_with_pos = []
for i, word in enumerate(data['text']):
    if word:
        words_with_pos.append({
            'word': word,
            'x': data['left'][i],
            'y': data['top'][i],
            'w': data['width'][i],
            'h': data['height'][i],
            'idx': i
        })

# Look for words that together form G.C.No
for i, w in enumerate(words_with_pos):
    x, y = w['x'], w['y']
    if x > 2400 and 500 < y < 800:
        # Check if this could be part of G.C.No
        word = w['word'].upper()
        if 'G' in word or 'C' in word or 'N' in word:
            # Show this and next few words
            nearby = [w['word']]
            for j in range(i+1, min(i+4, len(words_with_pos))):
                if abs(words_with_pos[j]['y'] - y) < 50:  # Same line
                    nearby.append(words_with_pos[j]['word'])
            print(f"  At ({x}, {y}): {' '.join(nearby)}")

print("\n" + "=" * 60)
