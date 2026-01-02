
import cv2
import os

path = r"c:\Users\avin4\.gemini\antigravity\brain\e4213f35-d609-471b-894b-bd215ca08950\page_1_delivery_robust.png"
if os.path.exists(path):
    img = cv2.imread(path)
    print(f"SIZE: {img.shape}")
else:
    print("File not found")
