import sys
import json
from datetime import datetime

sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')

print("Starting extraction...")
start = datetime.now()

from engine.extractors.client1 import run

result = run(r'c:\Users\avin4\Desktop\boostentryai ui code\1234567890120.pdf')

duration = (datetime.now() - start).total_seconds()

# Save results
with open('extraction_results.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\n\n{'='*80}")
print(f"EXTRACTION COMPLETED IN {duration:.1f} SECONDS")
print(f"{'='*80}\n")

# Print all fields
for key, value in result.items():
    if not key.startswith('_'):
        status = "✓" if value else "✗"
        print(f"{status} {key:35s}: {value}")

print(f"\n{'='*80}")
print(f"Results saved to: extraction_results.json")
print(f"{'='*80}")
