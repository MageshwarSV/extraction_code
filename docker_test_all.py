"""
Test extraction on ALL PDF files in uploads folder (inside Docker)
Processes all PDFs one by one and saves results to a txt file.
Writes INCREMENTALLY to avoid execution data loss on crash.
"""
import os
import json
import glob
import time
from engine.extractors.client1_format1 import run

# Find all PDF files in uploads folder
pdf_files = sorted(glob.glob("uploads/*.pdf"))

print(f"Found {len(pdf_files)} PDF files to process")
print("="*60)

output_file = "docker_all_pdfs_results.txt"
results = []
errors = []

# Initialize output file
with open(output_file, "w", encoding="utf-8") as f:
    f.write("Docker Extraction - All PDFs Results (Incremental)\n")
    f.write("="*60 + "\n\n")

for i, pdf_path in enumerate(pdf_files, 1):
    print(f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
    print("-"*40)
    
    try:
        start_time = time.time()
        result = run(pdf_path)
        duration = time.time() - start_time
        
        extracted = {
            "file": os.path.basename(pdf_path),
            "status": "success",
            "duration": f"{duration:.2f}s",
            "Invoice No": result.get("Invoice No"),
            "E-Way Bill No": result.get("E-Way Bill No"),
            "Delivery Address": result.get("Delivery Address", "")[:50] + "..." if result.get("Delivery Address") else None,
            "Vehicle": result.get("Vehicle"),
            "full_result": {
                k: v for k, v in result.items() if k not in ["pdf_path", "images"]
            }
        }
        results.append(extracted)
        print(f"  ✓ Invoice: {result.get('Invoice No')}")
        print(f"  ✓ E-Way: {result.get('E-Way Bill No')}")
        print(f"  ✓ Valid: {result.get('E-Way Bill Valid Upto')}")
        
    except Exception as e:
        error_info = {
            "file": os.path.basename(pdf_path),
            "status": "error",
            "error": str(e)
        }
        errors.append(error_info)
        extracted = error_info
        print(f"  ✗ ERROR: {e}")

    # Write this result immediately to file
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(extracted, ensure_ascii=False) + "\n")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Total PDFs processed: {len(pdf_files)}")
print(f"Successful: {len(results)}")
print(f"Errors: {len(errors)}")
print(f"Results saved to {output_file}")
