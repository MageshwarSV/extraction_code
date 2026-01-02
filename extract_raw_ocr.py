"""
Raw OCR Text Extraction Script
Extracts raw OCR text from PDF and saves to .txt file
Run this locally and in Docker to compare actual OCR output
"""

import os
import sys
import platform
import shutil
from pdf2image import convert_from_path
import pytesseract

# Detect Tesseract
def detect_tesseract():
    """Find Tesseract executable"""
    tess = shutil.which("tesseract")
    if tess:
        return tess
    
    # Windows fallback
    if platform.system() == "Windows":
        candidates = [
            r"C:\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    
    # Linux fallback
    candidates = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]
    for c in candidates:
        if os.path.exists(c):
            return c
    
    raise RuntimeError("Tesseract not found!")

# Detect Poppler (Windows only)
def detect_poppler():
    """Find Poppler path for Windows"""
    if platform.system() != "Windows":
        return None  # Linux uses system poppler
    
    candidates = [
        r"C:\poppler-25.07.0\Library\bin",
        r"C:\poppler-24.08.0\Library\bin",
        r"C:\poppler\Library\bin",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    
    # Check environment variable
    env_path = os.environ.get("POPPLER_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path
    
    return None

def extract_raw_ocr(pdf_path: str, output_txt: str, dpi: int = 300):
    """
    Extract raw OCR text from PDF and save to text file
    
    Args:
        pdf_path: Path to input PDF
        output_txt: Path to output text file
        dpi: DPI for PDF rendering (default 300)
    """
    print(f"=" * 60)
    print(f"RAW OCR TEXT EXTRACTION")
    print(f"=" * 60)
    print(f"PDF: {pdf_path}")
    print(f"Output: {output_txt}")
    print(f"DPI: {dpi}")
    print(f"Platform: {platform.system()}")
    
    # Setup Tesseract
    tess = detect_tesseract()
    pytesseract.pytesseract.tesseract_cmd = tess
    print(f"Tesseract: {tess}")
    
    # Get Tesseract version
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract Version: {version}")
    except:
        print(f"Tesseract Version: Unknown")
    
    # Setup Poppler
    poppler = detect_poppler()
    if poppler:
        print(f"Poppler: {poppler}")
    else:
        print(f"Poppler: System (Linux)")
    
    # Convert PDF to images
    print(f"\nRendering PDF at DPI {dpi}...")
    if poppler:
        pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler)
    else:
        pages = convert_from_path(pdf_path, dpi=dpi)
    
    print(f"Rendered {len(pages)} page(s)")
    
    # Extract OCR text from each page
    all_text = []
    for i, page in enumerate(pages):
        print(f"OCR processing page {i+1}/{len(pages)}...")
        text = pytesseract.image_to_string(page)
        all_text.append(f"{'='*60}\nPAGE {i+1}\n{'='*60}\n{text}")
    
    # Combine all text
    full_text = "\n\n".join(all_text)
    
    # Save to file
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(f"# Raw OCR Text Extraction\n")
        f.write(f"# PDF: {pdf_path}\n")
        f.write(f"# Platform: {platform.system()}\n")
        f.write(f"# DPI: {dpi}\n")
        f.write(f"# Tesseract: {tess}\n")
        f.write(f"# Date: {__import__('datetime').datetime.now().isoformat()}\n")
        f.write(f"\n")
        f.write(full_text)
    
    print(f"\n✓ Saved OCR text to: {output_txt}")
    print(f"Total characters: {len(full_text)}")
    
    # Print first 2000 chars as preview
    print(f"\n{'='*60}")
    print(f"PREVIEW (first 2000 chars)")
    print(f"{'='*60}")
    print(full_text[:2000])
    
    return full_text

if __name__ == "__main__":
    # Default PDF path
    pdf_path = "uploads/all problem.pdf"
    
    # Output filename based on platform
    if platform.system() == "Windows":
        output_file = "ocr_raw_local.txt"
    else:
        output_file = "ocr_raw_docker.txt"
    
    # Allow command line override
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Run extraction
    extract_raw_ocr(pdf_path, output_file)
