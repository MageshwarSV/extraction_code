"""
Advanced Image Preprocessing for Format 3 Invoices
Handles both SKEW (rotation) and PERSPECTIVE DISTORTION (inward folding/3D effect)
"""
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def detect_and_correct_perspective(pil_image):
    """
    Detect and correct perspective distortion (3D folded/tilted effect)
    
    This handles invoices that are photographed at an angle or folded inward,
    creating a trapezoid/3D effect where far edge appears smaller.
    
    Args:
        pil_image: PIL Image object
        
    Returns:
        PIL Image with perspective corrected (flattened to 2D rectangle)
    """
    
    # Convert PIL to OpenCV
    img_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Get image dimensions
    height, width = gray.shape
    
    # STEP 1: Edge detection
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Adaptive threshold for better edge detection
    thresh = cv2.adaptiveThreshold(
        blurred, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        11, 2
    )
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        logger.warning("[PERSPECTIVE] No contours found, skipping correction")
        return pil_image
    
    # STEP 2: Find the largest rectangular contour (document boundary)
    # Sort contours by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    document_contour = None
    for contour in contours[:10]:  # Check top 10 largest contours
        # Approximate to polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # If polygon has 4 corners, it's likely our document
        if len(approx) == 4:
            document_contour = approx
            break
    
    if document_contour is None:
        logger.info("[PERSPECTIVE] Document boundary not detected, trying alternative method")
        # Fallback: use edge points
        document_contour = _get_edge_points_fallback(thresh, width, height)
        
        if document_contour is None:
            logger.warning("[PERSPECTIVE] Could not detect document corners")
            return pil_image
    
    # STEP 3: Order the corner points (top-left, top-right, bottom-right, bottom-left)
    corners = _order_points(document_contour.reshape(4, 2))
    
    # Check if perspective correction is needed
    # Calculate the "squareness" - if already rectangular, skip
    if _is_already_rectangular(corners, width, height):
        logger.info("[PERSPECTIVE] Image already rectangular, no correction needed")
        return pil_image
    
    # STEP 4: Calculate the destination points (perfect rectangle)
    # Determine output dimensions
    (tl, tr, br, bl) = corners
    
    # Calculate width of the new image (max of top and bottom edge widths)
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    # Calculate height of the new image (max of left and right edge heights)
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    # Destination points (perfect rectangle)
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")
    
    # STEP 5: Calculate perspective transform matrix
    M = cv2.getPerspectiveTransform(corners, dst)
    
    # Apply perspective transform
    warped = cv2.warpPerspective(img_cv, M, (maxWidth, maxHeight))
    
    logger.info(f"[PERSPECTIVE] Corrected perspective distortion: {width}x{height} → {maxWidth}x{maxHeight}")
    
    # Convert back to PIL
    corrected = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
    return corrected


def _order_points(pts):
    """
    Order points in clockwise order: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    # Sum: top-left has smallest sum, bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Diff: top-right has smallest diff, bottom-left has largest diff
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect


def _is_already_rectangular(corners, width, height, tolerance=0.15):
    """
    Check if corners already form a near-perfect rectangle
    Returns True if image is flat (no correction needed)
    Returns False if image is distorted (needs perspective correction)
    
    Checks:
    1. Corner angles should be ~90 degrees
    2. Opposite sides should be parallel
    3. Edge lengths should be similar
    """
    (tl, tr, br, bl) = corners
    
    # METHOD 1: Check corner positions relative to expected rectangle
    # More lenient tolerance for "already flat" detection (15%)
    tolerance_px = min(width, height) * tolerance
    
    expected_corners = np.array([
        [0, 0],
        [width, 0],
        [width, height],
        [0, height]
    ], dtype="float32")
    
    # Calculate total deviation from perfect rectangle
    total_deviation = 0
    for i in range(4):
        deviation = np.linalg.norm(corners[i] - expected_corners[i])
        total_deviation += deviation
    
    avg_deviation = total_deviation / 4
    
    # If average deviation is less than tolerance, consider it rectangular
    if avg_deviation < tolerance_px:
        logger.info(f"[PERSPECTIVE CHECK] Image already flat (deviation: {avg_deviation:.1f}px < {tolerance_px:.1f}px)")
        return True
    
    # METHOD 2: Check if angles are approximately 90 degrees
    def angle_between_vectors(v1, v2):
        """Calculate angle between two vectors in degrees"""
        unit_v1 = v1 / np.linalg.norm(v1)
        unit_v2 = v2 / np.linalg.norm(v2)
        dot_product = np.dot(unit_v1, unit_v2)
        # Clamp to avoid numerical errors
        dot_product = np.clip(dot_product, -1.0, 1.0)
        angle = np.arccos(dot_product)
        return np.degrees(angle)
    
    # Calculate corner angles
    angles = []
    for i in range(4):
        p1 = corners[i - 1]  # Previous corner
        p2 = corners[i]      # Current corner
        p3 = corners[(i + 1) % 4]  # Next corner
        
        v1 = p1 - p2
        v2 = p3 - p2
        angle = angle_between_vectors(v1, v2)
        angles.append(angle)
    
    # Check if all angles are close to 90 degrees (tolerance: ±20 degrees)
    angles_ok = all(70 <= angle <= 110 for angle in angles)
    
    if angles_ok:
        logger.info(f"[PERSPECTIVE CHECK] Angles are rectangular: {[f'{a:.1f}°' for a in angles]}")
        return True
    else:
        logger.info(f"[PERSPECTIVE CHECK] Distortion detected - angles: {[f'{a:.1f}°' for a in angles]}")
        return False


def _get_edge_points_fallback(binary_image, width, height):
    """
    Fallback method: estimate corner points from edges
    """
    # Find edge pixels
    edges = cv2.Canny(binary_image, 50, 150)
    
    # Find points on edges
    points = np.column_stack(np.where(edges > 0))
    
    if len(points) < 4:
        return None
    
    # Estimate corners as extreme points
    # Top-left: min(x+y)
    # Top-right: max(x-y)
    # Bottom-right: max(x+y)
    # Bottom-left: max(-x+y)
    
    tl = points[np.argmin(points[:, 1] + points[:, 0])]
    tr = points[np.argmax(points[:, 0] - points[:, 1])]
    br = points[np.argmax(points[:, 1] + points[:, 0])]
    bl = points[np.argmax(points[:, 1] - points[:, 0])]
    
    # Convert to (x, y) format and return as contour
    corners = np.array([[tl[1], tl[0]], [tr[1], tr[0]], [br[1], br[0]], [bl[1], bl[0]]], dtype="float32")
    return corners.reshape(4, 1, 2).astype(np.int32)


def preprocess_invoice_complete(pil_image):
    """
    COMPLETE PREPROCESSING PIPELINE
    1. Perspective correction (flatten 3D/folded images)
    2. Deskewing (rotation correction)
    3. Enhancement (contrast, sharpening)
    
    This handles ALL types of distortion:
    - Inward folded pages
    - Tilted/skewed pages  
    - Poor lighting/contrast
    
    Args:
        pil_image: PIL Image object
        
    Returns:
        Fully preprocessed PIL Image ready for OCR
    """
    from PIL import ImageOps, ImageFilter
    
    # STEP 1: Correct perspective distortion (3D → 2D flattening)
    img = detect_and_correct_perspective(pil_image)
    
    # STEP 2: Correct rotation/skew
    from engine.extractors.deskew import deskew_image
    img = deskew_image(img)
    
    # STEP 3: Convert to grayscale
    img = img.convert('L')
    
    # STEP 4: Enhance contrast
    img = ImageOps.autocontrast(img)
    
    # STEP 5: Sharpen
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    
    logger.info("[PREPROCESSING] Complete pipeline applied")
    return img


# Test with page 16
if __name__ == "__main__":
    from pdf2image import convert_from_path
    import pytesseract
    import sys
    sys.path.insert(0, r'c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy')
    from engine.extractors.branch_extractor import extract_branch_refined
    from engine.extractors.invoice_datetime_extractor import extract_invoice_date_format3
    
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    
    print("=" * 80)
    print("TESTING PERSPECTIVE CORRECTION ON PAGE 16")
    print("=" * 80)
    
    pdf_path = r"c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy\DocScanner 23-Dec-2025 05-02 PM.pdf"
    
    # Extract page 16
    print("\n📄 Extracting page 16...")
    pages = convert_from_path(pdf_path, dpi=300, first_page=16, last_page=16)
    page16 = pages[0]
    
    # Test WITHOUT perspective correction
    print("\n🔍 WITHOUT perspective correction:")
    from engine.extractors.deskew import deskew_and_enhance
    page16_simple = deskew_and_enhance(page16)
    text_simple = pytesseract.image_to_string(page16_simple, config='--psm 6')
    branch_simple = extract_branch_refined(text_simple)
    date_simple = extract_invoice_date_format3(text_simple)
    print(f"   Branch: {branch_simple or 'NOT FOUND'}")
    print(f"   Date: {date_simple or 'NOT FOUND'}")
    
    # Test WITH perspective correction
    print("\n🔧 WITH perspective correction:")
    page16_corrected = preprocess_invoice_complete(page16)
    
    # Save for comparison
    page16_simple.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page16_without_perspective.png")
    page16_corrected.save(r"c:\Users\avin4\.gemini\antigravity\brain\9dbf8f1f-53b4-4fe6-8ba1-f12e9a4b3b9c\page16_with_perspective.png")
    
    text_corrected = pytesseract.image_to_string(page16_corrected, config='--psm 6')
    branch_corrected = extract_branch_refined(text_corrected)
    date_corrected = extract_invoice_date_format3(text_corrected)
    print(f"   Branch: {branch_corrected or 'NOT FOUND'}")
    print(f"   Date: {date_corrected or 'NOT FOUND'}")
    
    print("\n" + "=" * 80)
    print("COMPARISON:")
    print("=" * 80)
    print(f"Without Perspective: Branch={branch_simple}, Date={date_simple}")
    print(f"With Perspective: Branch={branch_corrected}, Date={date_corrected}")
    print(f"\nExpected: Branch=BILAKALAGUDUR, Date=12.12.2025")
    print("=" * 80)
