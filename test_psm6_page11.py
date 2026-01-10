# Test Page 11 vehicle with PSM 6
import sys
import os
sys.path.insert(0, os.getcwd())

from pdf2image import convert_from_path
import pytesseract
from engine.extractors.deskew import deskew_and_enhance
from engine.extractors.client2_format2 import extract_vehicle

pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
pages = convert_from_path(pdf_path, dpi=300, first_page=11, last_page=11)
page = pages[0]
page_corrected = deskew_and_enhance(page)

text_psm3 = pytesseract.image_to_string(page_corrected, config='--psm 3')
text_psm6 = pytesseract.image_to_string(page_corrected, config='--psm 6')

print("=" * 70)
print("PAGE 11 VEHICLE / E-WAY TEST")
print("=" * 70)

vehicle_psm3 = extract_vehicle(text_psm3)
vehicle_psm6 = extract_vehicle(text_psm6)

from engine.extractors.client2_format2 import extract_eway_bill_refined
eway_psm3 = extract_eway_bill_refined(text_psm3)
eway_psm6 = extract_eway_bill_refined(text_psm6)

print(f"PSM 3 Vehicle: {vehicle_psm3}")
print(f"PSM 6 Vehicle: {vehicle_psm6}")
print(f"PSM 3 E-Way:   {eway_psm3}")
print(f"PSM 6 E-Way:   {eway_psm6}")
