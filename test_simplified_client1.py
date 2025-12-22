"""
Test simplified client1.py on sample PDF
"""
import sys
import json
from datetime import datetime

# Add engine path
sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

from engine.extractors.client1 import run

# Test PDF path
pdf_path = r'c:\Users\avin4\Desktop\boostentryai ui code\1234567890120.pdf'

print("=" * 80)
print("TESTING SIMPLIFIED client1.py EXTRACTOR")
print("=" * 80)
print(f"PDF: {pdf_path}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()

start_time = datetime.now()

try:
    # Run extraction
    result = run(pdf_path)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)
    print(f"Duration: {duration:.2f} seconds")
    print(f"Fields Extracted: {sum(1 for v in result.values() if v is not None)}/{len(result)}")
    print("=" * 80)
    print()
    
    # Display all fields
    for field, value in result.items():
        if field.startswith('_'):  # Skip debug fields
            continue
        status = "✓" if value else "✗"
        print(f"{status} {field:30s}: {value}")
    
    print("\n" + "=" * 80)
    print("JSON OUTPUT")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Save to file
    output_file = r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\simplified_extraction_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, indent=2, ensure_ascii=False, fp=f)
    print(f"\n✓ Results saved to: {output_file}")
    
except Exception as e:
    print(f"\n✗ EXTRACTION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
