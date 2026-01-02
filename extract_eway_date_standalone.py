
import cv2
import pytesseract
import numpy as np
import os
import re
from pdf2image import convert_from_path
from PIL import Image

# Disable decompression bomb error
Image.MAX_IMAGE_PIXELS = None

def extract_eway_date_standalone(page_image, known_eway_no=None, page_num=0, debug=True):
    img_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
    
    # Preprocessing to ensure text is clear
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Try generic full page OCR first
    text = pytesseract.image_to_string(gray, config='--psm 6')
    
    if page_num == 11:
        with open(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\page11_raw.txt", "w", encoding="utf-8") as f:
            f.write(text)

    # If known number not found in text, try PSM 4 (Single Column) or PSM 3
    if known_eway_no and known_eway_no not in text:
         if debug: print(f"DEBUG Page {page_num}: Known No {known_eway_no} not found in PSM 6. Trying PSM 4...")
         text_psm4 = pytesseract.image_to_string(gray, config='--psm 4')
         text = text + "\n" + text_psm4
         if page_num == 11:
            with open(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\page11_raw.txt", "a", encoding="utf-8") as f:
                f.write("\n=== PSM 4 ===\n")
                f.write(text_psm4)

    patterns = []
    
    # 0. High Priority: Use Known E-Way Number if available
    if known_eway_no:
        # Regex to find KnownNumber - Date
        # Handle OCR variations: ./:/
        patterns.append(rf'{known_eway_no}\s*[\-–]\s*(\d{{2}}[\.\/\:]\d{{2}}[\.\/\:]\d{{4}})')

    # 1. Standard patterns (also with colon support)
    patterns.extend([
        r'E-?Way.*?Validity.*?(\d{12})\s*[\-–]\s*(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})',
        r'(\d{12})\s*[\-–]\s*(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})',
        r'Validity.*?(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})',
        r'E-?Way.*?No.*?(\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4})'
    ])
    
    lines = text.split('\n')
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # If we used the Known Number pattern (1 group) or Validity (1 group) vs Full (2 groups)
                if len(match.groups()) >= 2:
                    date_val = match.group(2)
                    if re.match(r'\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4}', date_val):
                        # Normalize colons to dots
                        date_val = date_val.replace(':', '.').replace('/', '.')
                        if debug: print(f"DEBUG Page {page_num}: Found Date (Pattern 2-grp): '{line.strip()[:60]}...' -> {date_val}")
                        return date_val
                elif len(match.groups()) == 1:
                    val = match.group(1)
                    if re.match(r'\d{2}[\.\/\:]\d{2}[\.\/\:]\d{4}', val):
                         # Normalize colons to dots
                         val = val.replace(':', '.').replace('/', '.')
                         if debug: print(f"DEBUG Page {page_num}: Found Date (Pattern 1-grp): '{line.strip()[:60]}...' -> {val}")
                         return val

    if debug: print(f"DEBUG Page {page_num}: No E-Way Date found.")
    return ""

if __name__ == "__main__":
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    target_pages = [2, 4, 6, 8, 10, 11, 14, 15, 16, 18, 20]
    
    print("\n=== Testing E-Way Date Extraction (Standard Patterns Only) ===")
    output_file = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\eway_date_clean.txt"
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, page in enumerate(pages):
                p_num = i + 1
                if p_num not in target_pages: continue
                
                # No known number - rely on standard patterns
                val = extract_eway_date_standalone(page, known_eway_no=None, page_num=p_num, debug=True)
                print(f"Page {p_num} E-Way Date: {val}")
                f.write(f"Page {p_num}: {val}\n")
    except Exception as e:
        print(f"Error: {e}")
