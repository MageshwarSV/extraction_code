
import os
import glob

# Try two common locations
paths = [
    r'C:\Tesseract-OCR\tessdata',
    r'C:\Program Files\Tesseract-OCR\tessdata',
    os.environ.get('TESSDATA_PREFIX', '')
]

tess_data = None
for p in paths:
    if p and os.path.exists(p):
        tess_data = p
        break

if tess_data:
    print(f'Checking models in: {tess_data}')
    files = glob.glob(os.path.join(tess_data, '*.traineddata'))
    
    print(f'Found {len(files)} model files:')
    print('-'*80)
    print(f"{'Filename':<30} | {'Size (MB)':<10} | {'Detected Type'}")
    print('-'*80)
    
    commands = []
    
    for f in files:
        name = os.path.basename(f)
        size_mb = os.path.getsize(f) / (1024*1024)
        
        # Determine type
        if size_mb > 10:
            mtype = 'BEST (High Accuracy)'
            # Use tessdata_best repo
            url = f'https://github.com/tesseract-ocr/tessdata_best/raw/main/{name}'
        elif size_mb < 2:
             # OSD or small component - usually in fast/std repo too
            mtype = 'OSD/Small'
            url = f'https://github.com/tesseract-ocr/tessdata_fast/raw/main/{name}'
        else:
            mtype = 'FAST (Standard)'
            url = f'https://github.com/tesseract-ocr/tessdata_fast/raw/main/{name}'
            
        print(f"{name:<30} | {size_mb:>9.2f} | {mtype}")
        commands.append(f'sudo wget -O "$TESS_PATH/{name}" {url}')
        
    print('-'*80)
    print('\n# COMMANDS TO RUN ON LINUX SERVER:')
    print('TESS_PATH=$(dpkg -L tesseract-ocr-eng | grep tessdata$ | head -n 1)')
    print('if [ -z "$TESS_PATH" ]; then TESS_PATH="/usr/share/tesseract-ocr/5/tessdata"; fi')
    print('echo "Downloading models to $TESS_PATH..."')
    print('\n'.join(commands))
else:
    print('Tesseract data dir not found in standard locations.')
