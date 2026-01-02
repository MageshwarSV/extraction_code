
import sys
import os
import cv2
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Add project root to path so we can import engine modules
sys.path.append(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

from engine.extractors.client1_format1 import extract_delivery_address_robust

def test_delivery_extraction():
    # Directory containing uploaded images
    artifacts_dir = r"c:\Users\avin4\.gemini\antigravity\brain\e4213f35-d609-471b-894b-bd215ca08950"
    
    # Listen to all png files
    import glob
    image_paths = glob.glob(os.path.join(artifacts_dir, "*.png"))
    
    if not image_paths:
        print("No images found to test.")
        return

    for image_path in image_paths:
        print(f"\nTesting extraction on: {image_path}")
        
        try:
            # Load image using OpenCV
            img = cv2.imread(image_path)
            if img is None:
                print("Error: Failed to load image.")
                continue

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            result = extract_delivery_address_robust(img_rgb, page_num=999, debug=True)
            
            print("-" * 20)
            print(f"RESULT for {os.path.basename(image_path)}:")
            print(f"'{result}'")
            print("-" * 20)
            
            if result:
                if "K001" in result:
                     print("SUCCESS: Found 'K001'")
                else:
                     print("WARNING: 'K001' not found")
                     
                if "Phone" in result or "State Code" in result:
                     print("FAILURE: Found unwanted bottom text")
                else:
                     print("SUCCESS: Cleanly cut off before bottom text")
            else:
                 print("WARNING: No result extracted (Header not found?)")

        except Exception as e:
            print(f"Exception during test: {e}")

if __name__ == "__main__":
    test_delivery_extraction()
