"""
Test client1_format1.py extraction on test123.pdf
"""
import sys
import os

# Add the project root to path
sys.path.insert(0, r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.client1_format1 import run
import json

PDF_PATH = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads\test123.pdf"

if __name__ == "__main__":
    print("=" * 60)
    print(f"Testing: {os.path.basename(PDF_PATH)}")
    print("=" * 60)
    
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        sys.exit(1)
    
    # Run extraction
    result = run(PDF_PATH)
    
    print("\n" + "=" * 60)
    print("EXTRACTION RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Highlight vehicle number if present
    if result and isinstance(result, dict):
        vehicle = result.get("Vehicle No.") or result.get("vehicle_no")
        if vehicle:
            print(f"\n>>> VEHICLE NUMBER: {vehicle}")
