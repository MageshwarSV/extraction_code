"""
Robust Image Deskewing for Format 3 Invoices
Corrects tilted/skewed images before OCR to improve accuracy
"""
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def deskew_image(pil_image, min_angle=-10, max_angle=10):
    """
    Detect and correct image skew/tilt using advanced OpenCV methods
    
    This handles invoices that are scanned at an angle (like page 11)
    
    Args:
        pil_image: PIL Image object
        min_angle: Minimum rotation angle to detect (default -10°)
        max_angle: Maximum rotation angle to detect (default +10°)
        
    Returns:
        PIL Image with skew corrected
    """
    
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # STEP 1: Preprocessing for better edge detection
    # Blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Threshold to get binary image
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # STEP 2: Detect skew angle using Hough Line Transform
    # This is more robust than minAreaRect for document skew
    edges = cv2.Canny(binary, 50, 150, apertureSize=3)
    
    # Detect lines
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is not None:
        # Calculate angles from detected lines
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            # Filter to reasonable skew range (-10° to +10°)
            if min_angle <= angle <= max_angle:
                angles.append(angle)
        
        if angles:
            # Use median angle (more robust than mean)
            skew_angle = np.median(angles)
            logger.info(f"[DESKEW] Detected skew angle: {skew_angle:.2f}°")
        else:
            # Fallback to minAreaRect method
            skew_angle = _detect_skew_fallback(binary)
            logger.info(f"[DESKEW] Fallback skew angle: {skew_angle:.2f}°")
    else:
        # Fallback if Hough Lines fails
        skew_angle = _detect_skew_fallback(binary)
        logger.info(f"[DESKEW] Fallback skew angle: {skew_angle:.2f}°")
    
    # STEP 3: Rotate image to correct skew
    if abs(skew_angle) > 0.1:  # Only rotate if angle is significant
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        
        # Calculate rotation matrix
        M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        
        # Perform rotation with white background
        rotated = cv2.warpAffine(
            img_cv, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)  # White background
        )
        
        # Convert back to PIL
        corrected = Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
        logger.info(f"[DESKEW] Image corrected by {skew_angle:.2f}°")
        return corrected
    else:
        logger.info("[DESKEW] No significant skew detected")
        return pil_image


def _detect_skew_fallback(binary_image):
    """
    Fallback skew detection using minimum area rectangle
    
    Args:
        binary_image: Binary image (threshold applied)
        
    Returns:
        Skew angle in degrees
    """
    # Find all white pixels
    coords = np.column_stack(np.where(binary_image > 0))
    
    if len(coords) == 0:
        return 0.0
    
    # Calculate minimum area rectangle
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    
    # Adjust angle to [-45, 45] range
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    return angle


def deskew_and_enhance(pil_image):
    """
    Complete preprocessing pipeline:
    1. Deskew (correct tilt)
    2. Enhance contrast
    3. Sharpen
    
    Args:
        pil_image: PIL Image object
        
    Returns:
        Preprocessed PIL Image ready for OCR
    """
    from PIL import ImageOps, ImageFilter
    
    # Step 1: Deskew
    img = deskew_image(pil_image)
    
    # Step 2: Convert to grayscale
    img = img.convert('L')
    
    # Step 3: Enhance contrast
    img = ImageOps.autocontrast(img)
    
    # Step 4: Slight sharpening
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    
    return img


# Test with page 11
if __name__ == "__main__":
    from pdf2image import convert_from_path
    import pytesseract
    import sys
    sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
    from engine.extractors.branch_extractor import extract_branch_refined
    
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    
    print("=" * 80)
    print("TESTING DESKEW ALGORITHM ON PAGE 11")
    print("=" * 80)
    
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    
    # Extract page 11
    print("\n📄 Extracting page 11...")
    pages = convert_from_path(pdf_path, dpi=300, first_page=11, last_page=11)
    page11 = pages[0]
    
    # Test WITHOUT deskew
    print("\n🔍 OCR WITHOUT deskew:")
    text_raw = pytesseract.image_to_string(page11, config='--psm 6')
    branch_raw = extract_branch_refined(text_raw)
    print(f"   Branch extracted: {branch_raw}")
    
    # Test WITH deskew
    print("\n🔧 Applying deskew algorithm...")
    page11_corrected = deskew_and_enhance(page11)
    
    # Save for comparison
    page11.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page11_before_deskew.png")
    page11_corrected.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page11_after_deskew.png")
    
    print("\n🔍 OCR AFTER deskew:")
    text_corrected = pytesseract.image_to_string(page11_corrected, config='--psm 6')
    branch_corrected = extract_branch_refined(text_corrected)
    print(f"   Branch extracted: {branch_corrected}")
    
    print("\n" + "=" * 80)
    print("COMPARISON:")
    print("=" * 80)
    print(f"Before: {branch_raw or 'NOT FOUND'}")
    print(f"After:  {branch_corrected or 'NOT FOUND'}")
    print(f"Expected: POTTANERI")
    print(f"Result: {'✅ SUCCESS!' if branch_corrected == 'POTTANERI' else '❌ FAILED'}")
    print("=" * 80)
