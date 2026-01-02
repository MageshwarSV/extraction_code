"""
Create annotated image showing field locations in Format 3 document
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Load the original image
img_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_page_1.png"
img = Image.open(img_path)
draw = ImageDraw.Draw(img)

# Try to use a decent font, fallback to default if not available
try:
    font_small = ImageFont.truetype("arial.ttf", 20)
    font_medium = ImageFont.truetype("arial.ttf", 24)
    font_large = ImageFont.truetype("arialbd.ttf", 28)
except:
    font_small = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_large = ImageFont.load_default()

# Define field annotations with approximate positions (x, y, label, priority)
# Priority: 1=High (red), 2=Medium (orange), 3=Low (yellow)
fields = [
    # Header section (top)
    (100, 60, "Company Name", 1, "red"),
    (900, 60, "Toll Free", 3, "yellow"),
    (100, 110, "CIN Number", 3, "yellow"),
    (100, 140, "PAN Number", 2, "orange"),
    (100, 170, "GST Number", 2, "orange"),
    
    # Invoice details (right side, top)
    (900, 180, "Invoice/ODN No", 1, "red"),
    (900, 220, "Invoice Date/Time", 1, "red"),
    (900, 260, "S.O. Number", 3, "yellow"),
    (900, 300, "DC Number", 3, "yellow"),
    
    # Buyer section (left column)
    (50, 400, "Buyer Name", 2, "orange"),
    (50, 480, "Buyer Address", 2, "orange"),
    (50, 620, "Buyer GSTIN", 2, "orange"),
    
    # Consignee section (right column)
    (850, 400, "Consignee Name", 1, "red"),
    (850, 480, "Consignee Address", 1, "red"),
    (850, 620, "Consignee GSTIN", 1, "red"),
    
    # Dispatch details
    (100, 750, "Dispatch From", 2, "orange"),
    (600, 750, "Dispatch To", 2, "orange"),
    (100, 790, "Incoterms", 3, "yellow"),
    (600, 790, "Shipment No", 3, "yellow"),
    
    # SP/Transporter details
    (100, 850, "SP/MMC Name", 3, "yellow"),
    (100, 900, "Transporter Name", 2, "orange"),
    (100, 950, "Vehicle Number", 1, "red"),
    (600, 950, "LR No/Date", 2, "orange"),
    
    # E-Way Bill section
    (100, 1000, "E-Way Bill No", 1, "red"),
    (400, 1000, "E-Way Validity", 1, "red"),
    (700, 1000, "Ack Number", 2, "orange"),
    
    # IRN
    (100, 1050, "IRN (Hash)", 2, "orange"),
    
    # Product table headers
    (100, 1150, "Product Name", 1, "red"),
    (500, 1150, "Packing Type", 2, "orange"),
    (700, 1150, "Qty (MT)", 1, "red"),
    (900, 1150, "Rate", 2, "orange"),
    (1100, 1150, "Amount", 1, "red"),
    
    # Product details
    (100, 1200, "HSN Code", 1, "red"),
    (100, 1250, "Batch/Week No", 3, "yellow"),
    
    # Tax section
    (900, 1400, "CGST", 2, "orange"),
    (900, 1440, "SGST", 2, "orange"),
    (900, 1520, "Total Amount", 1, "red"),
    
    # Amount in words
    (100, 1600, "Amount in Words", 1, "red"),
    
    # Contact
    (100, 1950, "Contact Name & Phone", 2, "orange"),
]

# Draw boxes and labels
for x, y, label, priority, color in fields:
    # Draw filled rectangle background for label
    bbox = draw.textbbox((x, y), label, font=font_small)
    padding = 5
    rect = [bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding]
    
    # Color based on priority
    if color == "red":
        fill_color = (255, 0, 0, 180)  # High priority - Red
        text_color = "white"
    elif color == "orange":
        fill_color = (255, 165, 0, 180)  # Medium priority - Orange
        text_color = "white"
    else:
        fill_color = (255, 255, 0, 180)  # Low priority - Yellow
        text_color = "black"
    
    # Draw rectangle and text
    draw.rectangle(rect, fill=fill_color[:3], outline=color, width=2)
    draw.text((x, y), label, fill=text_color, font=font_small)

# Add legend at the bottom
legend_y = img.height - 180
draw.rectangle([50, legend_y, img.width-50, legend_y+150], fill=(255, 255, 255), outline="black", width=3)
draw.text((70, legend_y+10), "FIELD PRIORITY LEGEND:", fill="black", font=font_medium)
draw.rectangle([70, legend_y+50, 120, legend_y+80], fill=(255, 0, 0))
draw.text((140, legend_y+55), "High Priority (Essential) - 12 fields", fill="black", font=font_small)
draw.rectangle([70, legend_y+90, 120, legend_y+120], fill=(255, 165, 0))
draw.text((140, legend_y+95), "Medium Priority (Important) - 8 fields", fill="black", font=font_small)
draw.rectangle([500, legend_y+50, 550, legend_y+80], fill=(255, 255, 0))
draw.text((570, legend_y+55), "Low Priority (Optional) - 20+ fields", fill="black", font=font_small)

# Save annotated image
output_path = r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\format3_annotated.png"
img.save(output_path, "PNG")
print(f"✅ Annotated image saved to: {output_path}")
print(f"   Image size: {img.size}")
print(f"   Total fields marked: {len(fields)}")
