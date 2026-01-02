"""
Debug: Compare gc_cropped.png reading vs gc_test_crop.png reading
"""
import cv2
import numpy as np
from PIL import Image

# Method 1: Direct cv2.imread (what find_otsu.py uses)
print("=== cv2.imread on gc_cropped.png ===")
img1 = cv2.imread("gc_cropped.png")
print(f"Shape: {img1.shape}")
print(f"BGR: B={np.mean(img1[:,:,0]):.1f}, G={np.mean(img1[:,:,1]):.1f}, R={np.mean(img1[:,:,2]):.1f}")

# Method 2: PIL then convert (what test_gc_e2e.py does)
print("\n=== PIL.Image.open then convert ===")
pil_img = Image.open("gc_test_crop.png")
img2 = np.array(pil_img)
print(f"Shape after np.array: {img2.shape}")
print(f"Is RGB: {img2.shape}")

# Convert RGB to BGR
if len(img2.shape) == 3:
    img2_bgr = cv2.cvtColor(img2, cv2.COLOR_RGB2BGR)
    print(f"BGR after conversion: B={np.mean(img2_bgr[:,:,0]):.1f}, G={np.mean(img2_bgr[:,:,1]):.1f}, R={np.mean(img2_bgr[:,:,2]):.1f}")
