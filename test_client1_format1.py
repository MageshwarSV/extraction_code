import sys
import json
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

print("="*80)
print("TESTING client1_format1.py")
print("="*80)

start = datetime.now()

try:
    from engine.extractors import client1_format1
    
    pdf_path = r'c:\Users\avin4\Desktop\boostentryai ui code\test\123456789012.pdf'
    print(f"PDF: {pdf_path}")
    print(f"Starting extraction at {start.strftime('%H:%M:%S')}")
    print("="*80)
    
    result = client1_format1.run(pdf_path)
    
    duration = (datetime.now() - start).total_seconds()
    
    print("\n" + "="*80)
    print(f"EXTRACTION COMPLETED in {duration:.1f} seconds")
    print("="*80)
    
    # Save results
    with open('test_extraction_results.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # Print all fields
    print("\nEXTRACTED FIELDS:")
    print("-"*80)
    for key, value in result.items():
        if not key.startswith('_'):
            status = "✓" if value else "✗"
            print(f"{status} {key:35s}: {value}")
    
    print("\n" + "="*80)
    print("Results saved to: test_extraction_results.json")
    print("="*80)
    
except Exception as e:
    print(f"\n✗ EXTRACTION FAILED!")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
