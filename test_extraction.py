import requests
import base64
import json

# Read the image
image_path = r"C:/Users/avin4/.gemini/antigravity/brain/018f4b53-b27a-4c35-a0eb-782b260cb122/uploaded_image_1764495489702.png"

with open(image_path, "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

# Make API request to extraction endpoint
url = "http://localhost:8000/api/extract"

payload = {
    "image": image_data,
    "template_id": "client1_format1"  # Adjust if needed
}

try:
    response = requests.post(url, json=payload, timeout=30)
    result = response.json()
    
    print("Extraction Result:")
    print(json.dumps(result, indent=2))
    
    # Save to file
    with open("extraction_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    print("\n✓ Result saved to extraction_result.json")
    
    # Print specific fields
    if "data" in result:
        print("\n=== Key Fields ===")
        for key in ["Consignee", "Consignor", "Source", "Destination", "Branch"]:
            if key in result["data"]:
                print(f"{key}: {result['data'][key]}")
                
except Exception as e:
    print(f"Error: {e}")
