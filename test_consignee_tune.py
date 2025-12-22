import json
from pathlib import Path

PDF = Path(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\larson and toubro.pdf")
print('PDF exists:', PDF.exists(), 'size=', PDF.stat().st_size if PDF.exists() else 'N/A')

from engine.extractors import client1_format1 as ex

res = ex.run(str(PDF))
print('\n=== Raw Data Summary ===')
print('Consignee (raw_data):', res.get('Consignee'))
print('Billing Party (raw_data):', res.get('Billing Party'))

# If OCR text is present, inspect it and run extract_consignee directly
ocr = res.get('OCR Text')
if ocr:
    print('\n=== Running extract_consignee on OCR text snippet ===')
    print('OCR snippet (first 800 chars):')
    print(ocr[:800])
    cand = ex.extract_consignee(ocr)
    print('\nextract_consignee returned:', cand)
else:
    print('No OCR Text available in raw data.')

# Save raw output for inspection
out_path = Path('consg_tune_output.json')
with out_path.open('w', encoding='utf-8') as f:
    json.dump(res, f, indent=2, ensure_ascii=False)
print('\nSaved full raw output to', out_path)
