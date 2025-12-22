"""
Smart OCR spacing detector - analyzes character-level bounding boxes to detect spaced initials
"""
import pytesseract
from PIL import Image
import re

def detect_spaced_initials(img: Image.Image, text: str) -> str:
    """
    Analyze character-level OCR data to detect if short uppercase words
    like "TRS" or "SLT" were originally spaced (e.g., "T R S").
    
    Returns the text with spaces added where appropriate.
    """
    try:
        # Get character-level bounding boxes
        boxes = pytesseract.image_to_boxes(img, config='--oem 1 --psm 6')
        
        # Parse the box data
        char_data = []
        for line in boxes.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    char = parts[0]
                    x1, y1, x2, y2 = map(int, parts[1:5])
                    char_data.append({
                        'char': char,
                        'x1': x1,
                        'x2': x2,
                        'y1': y1,
                        'y2': y2,
                        'width': x2 - x1
                    })
        
        # Find 2-3 letter uppercase words in the text
        pattern = r'\b([A-Z]{2,3})\b'
        
        def check_spacing(match):
            word = match.group(1)
            # Find this word in the character data
            # Look for sequences of these letters
            for i in range(len(char_data) - len(word) + 1):
                # Check if we have the right sequence of characters
                sequence = ''.join([char_data[j]['char'] for j in range(i, i + len(word))])
                if sequence == word:
                    # Analyze spacing between characters
                    gaps = []
                    for j in range(i, i + len(word) - 1):
                        gap = char_data[j + 1]['x1'] - char_data[j]['x2']
                        char_width = char_data[j]['width']
                        # Normalize gap by character width
                        normalized_gap = gap / char_width if char_width > 0 else 0
                        gaps.append(normalized_gap)
                    
                    # If average gap is large (> 0.5 character widths), it was likely spaced
                    if gaps and sum(gaps) / len(gaps) > 0.5:
                        # Add spaces
                        return ' '.join(list(word))
            
            return word
        
        # Replace words with spaced versions if detected
        result = re.sub(pattern, check_spacing, text)
        return result
        
    except Exception as e:
        print(f"Error in detect_spaced_initials: {e}")
        return text


# Test it
if __name__ == "__main__":
    from pdf2image import convert_from_path
    
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\pallipattu.pdf"
    
    images = convert_from_path(pdf_path, dpi=300)
    if images:
        img = images[0]
        
        # Get standard OCR text
        text = pytesseract.image_to_string(img, config='--oem 1 --psm 6')
        
        print("Original OCR text (first 500 chars):")
        print(text[:500])
        print("\n" + "=" * 80)
        
        # Apply spacing detection
        fixed_text = detect_spaced_initials(img, text)
        
        print("\nFixed text (first 500 chars):")
        print(fixed_text[:500])
        
        # Look for specific patterns
        print("\n" + "=" * 80)
        print("Checking for TRS/SLT patterns:")
        for line in fixed_text.split('\n')[:30]:
            if 'TRS' in line or 'T R S' in line or 'SLT' in line or 'S L T' in line:
                print(f"  {line}")
