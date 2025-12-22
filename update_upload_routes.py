# update_upload_routes.py
"""
Update upload_routes.py to:
1. Keep color images (no preprocessing)
2. Resize to 1700px max dimension
3. Compress JPEG to <300KB
4. Skip ocrmypdf (no text layer)
"""

filepath = r'c:\Users\avin4\Desktop\boostentryai ui code\automation_ui_code\boosterentryai-ui\routes\upload_routes.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Create the new convert_image_to_pdf_bytes function
new_function = '''def convert_image_to_pdf_bytes(raw_bytes: bytes) -> Tuple[bytes, str]:
    """
    Convert image to PDF - SIMPLE VERSION (like PDFKSS)
    - Keep color (no grayscale)
    - Resize to 1700px max
    - Compress to <300KB
    - NO text layer (let extraction engine handle OCR)
    """
    if not raw_bytes:
        raise ValueError("empty image bytes")
    
    from PIL import Image, ImageOps
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import io
    
    # Load image
    bio = io.BytesIO(raw_bytes)
    img = Image.open(bio)
    img.load()
    
    # Fix rotation using EXIF
    try:
        img = ImageOps.exif_transpose(img)
    except:
        pass
    
    # Resize to 1700px max (like PDFKSS)
    MAX_DIM = 1700
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = img.size
    
    # Keep color (RGB)
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    # Compress JPEG to <300KB
    TARGET_SIZE = 300 * 1024  # 300KB
    quality = 85
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG', quality=quality, optimize=True)
    
    while img_buffer.tell() > TARGET_SIZE and quality > 60:
        quality -= 5
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=quality, optimize=True)
    
    img_buffer.seek(0)
    
    # Create PDF with image (no text layer)
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(w, h))
    img_reader = ImageReader(img_buffer)
    c.drawImage(img_reader, 0, 0, width=w, height=h)
    c.save()
    
    return pdf_buffer.getvalue(), "application/pdf"
'''

# Find and replace the old function
import re

# Find the function definition
pattern = r'def convert_image_to_pdf_bytes\([^)]*\)[^:]*:.*?(?=\ndef [a-z_]|\nclass |\n@[a-z]|\nif __name__|$)'

match = re.search(pattern, content, re.DOTALL)

if match:
    content = content[:match.start()] + new_function + content[match.end():]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("SUCCESS: Updated upload_routes.py")
    print("Changes:")
    print("  - Removed all preprocessing (grayscale, denoise, etc.)")
    print("  - Resize to 1700px max")
    print("  - Compress JPEG to <300KB")
    print("  - NO ocrmypdf text layer")
    print("  - Simple 60-line function (was 300+ lines)")
else:
    print("ERROR: Could not find function to replace")
