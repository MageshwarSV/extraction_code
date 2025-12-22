import json
from pathlib import Path

pdf_path = Path(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\larson and toubro.pdf")
print('PDF exists:', pdf_path.exists(), 'size_bytes=', pdf_path.stat().st_size if pdf_path.exists() else 'N/A')

from engine.extractors import client1_format1 as extractor

try:
    result = extractor.run(str(pdf_path))
    keys = ["Consignee", "Billing Party", "Consignee Raw", "Billing Raw"]
    out = {k: result.get(k) for k in keys if k in result}
    print(json.dumps(out, indent=2, ensure_ascii=False))
except Exception as e:
    import traceback
    print('ERROR during extractor.run:', e)
    traceback.print_exc()
