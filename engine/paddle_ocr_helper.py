"""
PaddleOCR Helper - Wrapper for PaddleOCR
Replaces pytesseract functionality with PaddleOCR
"""
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np

# Initialize PaddleOCR (do this once)
_ocr_instance = None

def get_paddle_ocr():
    """Get or create PaddleOCR instance (singleton)"""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    return _ocr_instance


def image_to_string(image, config=None):
    """
    PaddleOCR equivalent of pytesseract.image_to_string()
    
    Args:
        image: PIL Image object
        config: Ignored (for compatibility with pytesseract calls)
        
    Returns:
        Extracted text as string
    """
    ocr = get_paddle_ocr()
    
    # Convert PIL to numpy array
    img_array = np.array(image)
    
    # Run OCR
    result = ocr.ocr(img_array, cls=True)
    
    # Extract text from result
    if not result or not result[0]:
        return ""
    
    text_lines = []
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]  # [1][0] contains the text
            text_lines.append(text)
    
    return '\n'.join(text_lines)


def image_to_data(image, config=None, output_type=None):
    """
    PaddleOCR equivalent of pytesseract.image_to_data()
    Returns dictionary with text and confidence scores
    
    Args:
        image: PIL Image object
        config: Ignored
        output_type: Ignored
        
    Returns:
        Dictionary with 'text' and 'conf' lists
    """
    ocr = get_paddle_ocr()
    
    # Convert PIL to numpy array
    img_array = np.array(image)
    
    # Run OCR
    result = ocr.ocr(img_array, cls=True)
    
    # Format as pytesseract-like dictionary
    data = {
        'text': [],
        'conf': []
    }
    
    if not result or not result[0]:
        return data
    
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]  # Text
            conf = float(line[1][1]) * 100  # Confidence (0-1) -> (0-100)
            
            # Split into words
            words = text.split()
            for word in words:
                data['text'].append(word)
                data['conf'].append(int(conf))
    
    return data
