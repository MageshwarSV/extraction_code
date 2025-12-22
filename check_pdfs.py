# check_pdfs.py
import os
import fitz

pdfkss = r'c:\Users\avin4\Desktop\boostentryai ui code\pdfkss'
test = r'c:\Users\avin4\Desktop\boostentryai ui code\test'

print("PDFKSS FOLDER:")
for f in os.listdir(pdfkss)[:3]:
    if f.endswith('.pdf'):
        path = os.path.join(pdfkss, f)
        size = os.path.getsize(path) // 1024
        doc = fitz.open(path)
        text_len = len(doc[0].get_text().strip())
        doc.close()
        print(f"  {f}: Size={size}KB, TextChars={text_len}")

print("\nTEST FOLDER:")
for f in os.listdir(test)[:3]:
    if f.endswith('.pdf'):
        path = os.path.join(test, f)
        size = os.path.getsize(path) // 1024
        doc = fitz.open(path)
        text_len = len(doc[0].get_text().strip())
        doc.close()
        print(f"  {f}: Size={size}KB, TextChars={text_len}")
