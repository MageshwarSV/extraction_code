import pytesseract
from PIL import Image, ImageDraw, ImageFont

# Check if Tesseract is accessible
print("Testing Tesseract OCR...")
print(f"Tesseract version: {pytesseract.get_tesseract_version()}")
print(f"Tesseract path: {pytesseract.pytesseract.tesseract_cmd}")

# Create a simple test image with text
img = Image.new('RGB', (400, 100), color='white')
draw = ImageDraw.Draw(img)

# Draw some text
try:
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

draw.text((10, 30), "Hello Tesseract", fill='black', font=font)

# Save test image
test_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\test_ocr.png"
img.save(test_path)
print(f"\nTest image saved: {test_path}")

# Try OCR
text = pytesseract.image_to_string(img)
print(f"\nOCR Result: '{text.strip()}'")
print(f"OCR Result length: {len(text)} characters")

if "Hello" in text or "Tesseract" in text:
    print("\n✅ Tesseract OCR is working!")
else:
    print("\n❌ Tesseract OCR returned unexpected result")
