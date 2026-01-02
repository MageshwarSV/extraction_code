#!/usr/bin/env python
"""
Test script to verify vehicle number extraction (with 11+ char fix) on all PDFs in uploads folder.
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.client1_format1 import run

UPLOADS_DIR = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\uploads"

def test_all_pdfs():
    """Test extraction on all PDFs in uploads folder and show vehicle numbers"""
    
    results = []
    errors = []
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(UPLOADS_DIR) if f.lower().endswith('.pdf')]
    
    print(f"\n{'='*80}")
    print(f"Testing vehicle extraction on {len(pdf_files)} PDFs")
    print(f"{'='*80}\n")
    
    for i, pdf_file in enumerate(sorted(pdf_files), 1):
        pdf_path = os.path.join(UPLOADS_DIR, pdf_file)
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file}")
        
        try:
            result = run(pdf_path)
            vehicle = result.get("Vehicle")
            invoice = result.get("Invoice No")
            
            # Check vehicle number length
            status = "✓"
            warning = ""
            if vehicle:
                if len(vehicle) > 10:
                    status = "⚠"
                    warning = f" (STILL {len(vehicle)} chars!)"
                elif len(vehicle) == 10:
                    warning = " (10 chars ✓)"
                else:
                    warning = f" ({len(vehicle)} chars)"
            else:
                status = "✗"
                warning = " (NOT FOUND)"
            
            results.append({
                "file": pdf_file,
                "vehicle": vehicle,
                "vehicle_len": len(vehicle) if vehicle else 0,
                "invoice": invoice,
                "status": status
            })
            
            print(f"    {status} Vehicle: {vehicle or 'None'}{warning}")
            print(f"      Invoice: {invoice or 'Not found'}")
            
        except Exception as e:
            errors.append({
                "file": pdf_file,
                "error": str(e)
            })
            print(f"    ✗ ERROR: {str(e)[:100]}")
        
        print()
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    
    # Count results
    found = [r for r in results if r["vehicle"]]
    oversized = [r for r in found if r["vehicle_len"] > 10]
    normal = [r for r in found if r["vehicle_len"] <= 10]
    not_found = [r for r in results if not r["vehicle"]]
    
    print(f"Total PDFs tested: {len(pdf_files)}")
    print(f"Vehicle found: {len(found)}")
    print(f"  - Normal (≤10 chars): {len(normal)}")
    print(f"  - Oversized (>10 chars): {len(oversized)}")
    print(f"Vehicle not found: {len(not_found)}")
    print(f"Errors: {len(errors)}")
    
    if oversized:
        print(f"\n⚠ OVERSIZED VEHICLE NUMBERS:")
        for r in oversized:
            print(f"   {r['file']}: {r['vehicle']} ({r['vehicle_len']} chars)")
    
    if errors:
        print(f"\n✗ ERRORS:")
        for e in errors:
            print(f"   {e['file']}: {e['error'][:80]}")
    
    print(f"\n{'='*80}")
    print("All vehicles extracted:")
    print(f"{'='*80}")
    for r in sorted(results, key=lambda x: x['file']):
        if r["vehicle"]:
            print(f"  {r['file']}: {r['vehicle']} ({r['vehicle_len']} chars)")


if __name__ == "__main__":
    test_all_pdfs()
