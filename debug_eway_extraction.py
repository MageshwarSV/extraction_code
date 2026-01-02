import re

with open('ocr_raw_local.txt', 'r', encoding='utf-8') as f:
    local = f.read()
with open('ocr_raw_docker.txt', 'r', encoding='utf-8') as f:
    docker = f.read()

output = []

output.append('=== LOCAL lines with EWB (digits stripped) ===')
for line in local.splitlines():
    if re.search(r'EWB|EWE', line, re.IGNORECASE):
        digits = re.sub(r'[^0-9]', '', line)
        output.append(f'Line: {repr(line[:100])}')
        output.append(f'Digits: {digits}')
        output.append(f'Length: {len(digits)}')
        if len(digits) >= 12:
            output.append(f'First 12: {digits[:12]}')
        output.append('')

output.append('')
output.append('=== DOCKER lines with EWB (digits stripped) ===')
for line in docker.splitlines():
    if re.search(r'EWB|EWE', line, re.IGNORECASE):
        digits = re.sub(r'[^0-9]', '', line)
        output.append(f'Line: {repr(line[:100])}')
        output.append(f'Digits: {digits}')
        output.append(f'Length: {len(digits)}')
        if len(digits) >= 12:
            output.append(f'First 12: {digits[:12]}')
        output.append('')

with open('eway_debug_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
    
print('Saved to eway_debug_result.txt')
