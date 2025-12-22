#!/usr/bin/env python3
"""
CRITICAL INSIGHT CHECK:
Does PDFKSS actually have an embedded text layer?
If YES, that's why it's fast (no OCR needed!)
"""

import fitz

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss\1.pdf'
captured = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\optimized_test.pdf'

print("="*80)
print("TEXT LAYER CHECK - Is this the REAL difference?")
print("="*80)

def check_text_layer(path, name):
    print(f"\n[{name}]")
    doc = fitz.open(path)
    page = doc[0]
    text = page.get_text().strip()
    
    print(f"  Text length: {len(text)}")
    print(f"  Has embedded text: {'YES' if len(text) > 100 else 'NO'}")
    
    if len(text) > 100:
        print(f"  Preview: {text[:200]}...")
        print(f"\n  *** THIS PDF HAS TEXT LAYER - USES FAST PATH! ***")
    else:
        print(f"  *** NO TEXT LAYER - NEEDS OCR (SLOW PATH) ***")
    
    doc.close()
    return len(text) > 100

pdfkss_has_text = check_text_layer(pdfkss, "PDFKSS (Scanner)")
captured_has_text = check_text_layer(captured, "CAPTURED IMAGE (Camera)")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if pdfkss_has_text and not captured_has_text:
    print("\n*** FOUND THE ISSUE! ***")
    print("\nPDFKSS is fast because:")
    print("  - It has an EMBEDDED TEXT LAYER")
    print("  - Engine uses FAST PATH (no OCR!")
    print("  - Just extracts text directly from PDF")
    print("\nCaptured images are slow because:")
    print("  - NO text layer")
    print("  - Engine must run FULL OCR")
    print("  - Tesseract + PaddleOCR = slow")
    print("\nSOLUTION:")
    print("  → Add text layer to captured images BEFORE upload!")
    print("  → Use ocrmypdf in upload_routes.py")
    print("  → Then they'll use fast path too!")
elif not pdfkss_has_text and not captured_has_text:
    print("\nBoth need OCR - the difference must be image quality")
else:
    print("\nUnexpected result - need more investigation")
