"""
Compare the TWO images - what's different?
"""
import cv2
import numpy as np

# Working purple image (gave 14549)
PURPLE = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767219542625.png"
# Non-working pink image (gave 2)
PINK = r"C:/Users/avin4/.gemini/antigravity/brain/e4213f35-d609-471b-894b-bd215ca08950/uploaded_image_1767219729115.png"

purple_img = cv2.imread(PURPLE)
pink_img = cv2.imread(PINK)

print("=== PURPLE (Working) ===")
print(f"Shape: {purple_img.shape}")
purple_hsv = cv2.cvtColor(purple_img, cv2.COLOR_BGR2HSV)
# Sample center pixel
cy, cx = purple_img.shape[0]//2, purple_img.shape[1]//2
print(f"Center pixel BGR: {purple_img[cy, cx]}")
print(f"Center pixel HSV: {purple_hsv[cy, cx]}")
print(f"Mean H: {np.mean(purple_hsv[:,:,0]):.1f}")
print(f"Mean S: {np.mean(purple_hsv[:,:,1]):.1f}")
print(f"Mean V: {np.mean(purple_hsv[:,:,2]):.1f}")

print("\n=== PINK (Not Working) ===")
print(f"Shape: {pink_img.shape}")
pink_hsv = cv2.cvtColor(pink_img, cv2.COLOR_BGR2HSV)
cy, cx = pink_img.shape[0]//2, pink_img.shape[1]//2
print(f"Center pixel BGR: {pink_img[cy, cx]}")
print(f"Center pixel HSV: {pink_hsv[cy, cx]}")
print(f"Mean H: {np.mean(pink_hsv[:,:,0]):.1f}")
print(f"Mean S: {np.mean(pink_hsv[:,:,1]):.1f}")
print(f"Mean V: {np.mean(pink_hsv[:,:,2]):.1f}")

# Check gray
purple_gray = cv2.cvtColor(purple_img, cv2.COLOR_BGR2GRAY)
pink_gray = cv2.cvtColor(pink_img, cv2.COLOR_BGR2GRAY)

print(f"\nPurple gray mean: {np.mean(purple_gray):.1f}")
print(f"Pink gray mean: {np.mean(pink_gray):.1f}")
