
import sys
import os
import cv2
import pytesseract

# Setup paths
sys.path.append(r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy")

def check_crop_content():
    # 1. The Result we generated (Local fresh copy)
    generated_crop = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\gc_crops_verify\delivery_debug_f1\page_1_delivery_robust.png"
    
    # 2. The User's "Desired" image (based on visual description, this is the shorter one)
    # uploaded_image_1 has less text at bottom
    user_target = r"C:\Users\avin4\.gemini\antigravity\brain\e4213f35-d609-471b-894b-bd215ca08950\uploaded_image_1_1767005167795.png"

    print("-" * 40)
    print("COMPARISON REPORT")
    print("-" * 40)
    
    if os.path.exists(generated_crop):
        try:
            img_gen = cv2.imread(generated_crop)
            if img_gen is None:
                print("Error: Could not read generated crop message.")
            else:
                print(f"Generated Crop Size: {img_gen.shape}")
                text_gen = pytesseract.image_to_string(img_gen).strip()
                print(f"\n[GENERATED CROP TEXT START]\n{text_gen}\n[GENERATED CROP TEXT END]")
                
                # Check for unwanted markers
                unwanted = ["Phone", "State Code", "Mob", "Email"]
                found_unwanted = [u for u in unwanted if u in text_gen or u.upper() in text_gen.upper()]
                
                if found_unwanted:
                    print(f"\n>>> FAILED: Generated crop contains unwanted text: {found_unwanted}")
                else:
                    print("\n>>> SUCCESS: Generated crop is clean (no bottom text found).")
        except Exception as e:
            print(f"Error processing generated crop: {e}")
            
    else:
        print("Generated crop file not found.")

    print("-" * 20)

    if os.path.exists(user_target):
        try:
            img_user = cv2.imread(user_target)
            if img_user is None:
                 print("Error reading user target.")
            else:
                 text_user = pytesseract.image_to_string(img_user).strip()
                 print(f"\n[USER TARGET TEXT START]\n{text_user}\n[USER TARGET TEXT END]")
        except Exception as e:
            print(f"Error processing user target: {e}")
    else:
        print("User target image not found.")


if __name__ == "__main__":
    check_crop_content()
