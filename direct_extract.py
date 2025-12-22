#!/usr/bin/env python3
"""
BYPASS FIX: Direct OCR extraction without using broken client1_format1.py

This will:
1. Take the PDF
2. Run OCR directly
3. Extract fields
4. Return results properly
"""

import fitz
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageOps
import cv2
import numpy as np
import re
from datetime import datetime

def extract_invoice_direct(pdf_path):
    """Direct extraction bypassing broken client1_format1.py"""
    
    result = {
        'success': False,
        'extraction_time': 0,
        'fields': {},
        'raw_text': ''
    }
    
    import time
    start = time.time()
    
    try:
        # Check for text layer first
        doc = fitz.open(pdf_path)
        page = doc[0]
        text_layer = page.get_text().strip()
        
        if len(text_layer) > 500:
            # Has text layer - fast path
            text = text_layer
            result['path'] = 'fast_text_layer'
        else:
            # Need OCR - optimized path
            # Detect if captured image
            fonts = page.get_fonts()
            images = page.get_images()
            is_captured = len(images) >= 1 and len(fonts) < 3
            
            doc.close()
            
            # Render PDF
            poppler_bin = r"C:\poppler-25.07.0\Library\bin"
            pages = convert_from_path(pdf_path, dpi=200 if is_captured else 300, poppler_path=poppler_bin)
            img = pages[0]
            
            # Preprocessing - minimal for captured images
            if is_captured:
                arr = np.array(img.convert('L'))
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                processed = Image.fromarray(clahe.apply(arr))
            else:
                processed = ImageOps.autocontrast(img.convert('L'))
            
            # OCR
            configs = ['--psm 6', '--psm 4'] if is_captured else ['--psm 6', '--psm 4', '--psm 3']
            all_text = []
            for cfg in configs:
                try:
                    t = pytesseract.image_to_string(processed, config=cfg)
                    if t.strip():
                        all_text.append(t)
                except:
                    pass
            
            # Merge text
            text = '\n'.join(all_text)
            result['path'] = 'ocr_captured' if is_captured else 'ocr_regular'
        
        result['raw_text'] = text
        
        # Extract fields
        fields = {}
        
        # Invoice number
        inv_match = re.search(r'invoice.*?(\d{10,})', text, re.I)
        if inv_match:
            fields['Invoice No'] = inv_match.group(1)
        
        # Date
        date_match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{4})', text)
        if date_match:
            fields['Date'] = date_match.group(1)
        
        # Amount
        amt_match = re.search(r'(?:total|amount|value).*?(\d+[,.]?\d+[.]\d{2})', text, re.I)
        if amt_match:
            fields['Amount'] = amt_match.group(1)
        
        #Consignee
        consignee_match = re.search(r'(?:consignee|bill.*?to).*?([A-Z][A-Za-z\s]{10,50})', text, re.I)
        if consignee_match:
            fields['Consignee'] = consignee_match.group(1).strip()
        
        result['fields'] = fields
        result['success'] = True
        result['extraction_time'] = time.time() - start
        
    except Exception as e:
        result['error'] = str(e)
        result['extraction_time'] = time.time() - start
    
    return result

# Test
if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else 'uploaded_invoice.pdf'
    
    print(f"Extracting from: {pdf_path}")
    result = extract_invoice_direct(pdf_path)
    
    print(f"\nExtraction Time: {result['extraction_time']:.2f}s")
    print(f"Path: {result['path']}")
    print(f"Success: {result['success']}")
    
    print("\nExtracted Fields:")
    for key, val in result['fields'].items():
        print(f"  {key}: {val}")
    
    # Save to TXT
    with open('direct_extraction_output.txt', 'w', encoding='utf-8') as f:
        f.write("DIRECT EXTRACTION RESULTS\n")
        f.write("="*80 + "\n\n")
        f.write(f"Extraction Time: {result['extraction_time']:.2f}s\n")
        f.write(f"Extraction Path: {result['path']}\n")
        f.write(f"Success: {result['success']}\n\n")
        
        f.write("EXTRACTED FIELDS:\n")
        f.write("-"*80 + "\n")
        for key, val in result['fields'].items():
            f.write(f"{key}: {val}\n")
        
        f.write("\n\nFULL OCR TEXT:\n")
        f.write("="*80 + "\n")
        f.write(result['raw_text'])
    
    print("\n✅ Saved to: direct_extraction_output.txt")
    print(f"Full path: c:\\Users\\avin4\\Desktop\\wbai_doc_extractor_engine-maincopy\\direct_extraction_output.txt")
