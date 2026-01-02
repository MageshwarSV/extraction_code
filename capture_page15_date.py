# Capture Page 15 snippet for date
from pdf2image import convert_from_path
import os

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
pages = convert_from_path(pdf_path, dpi=300, first_page=15, last_page=15)
page = pages[0]

# Save full page and a crop of the top right where the date usually is
page.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page15_full.png")

# Crop top right (typical location for Format 3 date)
# JSW Format 3 date is usually in the top right box
width, height = page.size
crop = page.crop((width*0.5, 0, width, height*0.3))
crop.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page15_date_crop.png")
