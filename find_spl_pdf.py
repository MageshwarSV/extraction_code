# find_spl_pdf.py
import os
import fitz  # PyMuPDF

test_folder = r'c:\Users\avin4\Desktop\boostentryai ui code\test'
pdfs = [f for f in os.listdir(test_folder) if f.lower().endswith('.pdf')]

print(f"Scanning {len(pdfs)} PDFs for 'SPL Infrastructure'...")

for pdf_name in pdfs:
    pdf_path = os.path.join(test_folder, pdf_name)
    try:
        doc = fitz.open(pdf_path)
        found = False
        for page in doc:
            text = page.get_text()
            if "SPL" in text and "Infrastructure" in text:
                print(f"FOUND_FILE: {pdf_name}")
                found = True
                break
        if found:
            break
    except Exception as e:
        print(f"Error reading {pdf_name}: {e}")
