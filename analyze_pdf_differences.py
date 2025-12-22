# analyze_pdf_differences.py
"""
Compare PDFs from pdfkss folder vs test folder to understand differences in:
- File size
- Has text layer or not
- Text layer quality (character count)
- Image DPI/resolution
- Number of pages
- Extraction time
"""
import os
import sys
import time
import fitz  # PyMuPDF
from pathlib import Path

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

def analyze_pdf(pdf_path):
    """Analyze a single PDF and return its characteristics"""
    result = {
        'path': pdf_path,
        'filename': os.path.basename(pdf_path),
        'size_kb': os.path.getsize(pdf_path) / 1024,
        'pages': 0,
        'has_text_layer': False,
        'text_layer_chars': 0,
        'image_count': 0,
        'avg_image_dpi': 0,
        'extraction_time': 0,
    }
    
    try:
        doc = fitz.open(pdf_path)
        result['pages'] = len(doc)
        
        # Check text layer
        full_text = ""
        total_images = 0
        total_dpi = 0
        
        for page in doc:
            # Text layer
            text = page.get_text()
            full_text += text
            
            # Images
            images = page.get_images()
            total_images += len(images)
            
            # Image DPI (approximate from page size vs image size)
            for img in images:
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image:
                        img_width = base_image.get('width', 0)
                        page_width = page.rect.width
                        if page_width > 0 and img_width > 0:
                            dpi = int(img_width / (page_width / 72))
                            total_dpi += dpi
                except:
                    pass
        
        result['text_layer_chars'] = len(full_text.strip())
        result['has_text_layer'] = len(full_text.strip()) > 100
        result['image_count'] = total_images
        result['avg_image_dpi'] = total_dpi // total_images if total_images > 0 else 0
        
        doc.close()
        
        # Measure extraction time
        from engine.extractors.client1_format1 import run
        start = time.time()
        try:
            run(pdf_path)
        except Exception as e:
            print(f"  Extraction failed: {e}")
        result['extraction_time'] = round(time.time() - start, 2)
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def main():
    pdfkss_folder = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss'
    test_folder = r'c:\Users\avin4\Desktop\boostentryai ui code\test'
    
    print("=" * 80)
    print("PDF ANALYSIS: pdfkss vs test folders")
    print("=" * 80)
    
    # Analyze pdfkss folder
    print("\n📁 PDFKSS FOLDER:")
    print("-" * 40)
    pdfkss_results = []
    if os.path.exists(pdfkss_folder):
        pdfs = [f for f in os.listdir(pdfkss_folder) if f.lower().endswith('.pdf')][:3]  # Limit to 3
        for pdf in pdfs:
            pdf_path = os.path.join(pdfkss_folder, pdf)
            print(f"\nAnalyzing: {pdf}")
            result = analyze_pdf(pdf_path)
            pdfkss_results.append(result)
            print(f"  Size: {result['size_kb']:.1f} KB")
            print(f"  Pages: {result['pages']}")
            print(f"  Has Text Layer: {result['has_text_layer']} ({result['text_layer_chars']} chars)")
            print(f"  Images: {result['image_count']}, Avg DPI: {result['avg_image_dpi']}")
            print(f"  Extraction Time: {result['extraction_time']}s")
    else:
        print("  Folder not found!")
    
    # Analyze test folder
    print("\n📁 TEST FOLDER:")
    print("-" * 40)
    test_results = []
    if os.path.exists(test_folder):
        pdfs = [f for f in os.listdir(test_folder) if f.lower().endswith('.pdf')][:3]  # Limit to 3
        for pdf in pdfs:
            pdf_path = os.path.join(test_folder, pdf)
            print(f"\nAnalyzing: {pdf}")
            result = analyze_pdf(pdf_path)
            test_results.append(result)
            print(f"  Size: {result['size_kb']:.1f} KB")
            print(f"  Pages: {result['pages']}")
            print(f"  Has Text Layer: {result['has_text_layer']} ({result['text_layer_chars']} chars)")
            print(f"  Images: {result['image_count']}, Avg DPI: {result['avg_image_dpi']}")
            print(f"  Extraction Time: {result['extraction_time']}s")
    else:
        print("  Folder not found!")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)
    
    if pdfkss_results:
        avg_size = sum(r['size_kb'] for r in pdfkss_results) / len(pdfkss_results)
        avg_text = sum(r['text_layer_chars'] for r in pdfkss_results) / len(pdfkss_results)
        avg_time = sum(r['extraction_time'] for r in pdfkss_results) / len(pdfkss_results)
        has_text = sum(1 for r in pdfkss_results if r['has_text_layer']) / len(pdfkss_results) * 100
        print(f"\nPDFKSS: Avg Size={avg_size:.1f}KB, Avg Text={avg_text:.0f} chars, Has Text={has_text:.0f}%, Avg Time={avg_time:.2f}s")
    
    if test_results:
        avg_size = sum(r['size_kb'] for r in test_results) / len(test_results)
        avg_text = sum(r['text_layer_chars'] for r in test_results) / len(test_results)
        avg_time = sum(r['extraction_time'] for r in test_results) / len(test_results)
        has_text = sum(1 for r in test_results if r['has_text_layer']) / len(test_results) * 100
        print(f"TEST:   Avg Size={avg_size:.1f}KB, Avg Text={avg_text:.0f} chars, Has Text={has_text:.0f}%, Avg Time={avg_time:.2f}s")

if __name__ == "__main__":
    main()
