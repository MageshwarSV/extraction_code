
import sys
import logging
import numpy as np
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("LinuxCheck")

print("="*60)
print("VERIFYING RAPIDOCR FOR LINUX (CPU MODE)")
print("="*60)

# 1. Check Import
try:
    from rapidocr_onnxruntime import RapidOCR
    print("✅ Library 'rapidocr_onnxruntime' imported successfully.")
except ImportError:
    print("❌ ERROR: 'rapidocr_onnxruntime' is not installed.")
    print("   Run: pip install rapidocr_onnxruntime")
    sys.exit(1)

# 2. Check Initialization (Load Models)
try:
    print("⏳ Initializing RapidOCR engine (loading ONNX models)...")
    # det_use_cuda=False ensures CPU mode
    engine = RapidOCR(det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False)
    print("✅ Engine initialized successfully.")
except Exception as e:
    print(f"❌ ERROR: Failed to initialize engine.")
    print(f"   Error: {e}")
    sys.exit(1)

# 3. Check Execution (Run Inference)
try:
    print("⏳ Running test inference (simulated image)...")
    
    # Create white image with black text "GC12345"
    img = np.ones((100, 300, 3), dtype=np.uint8) * 255
    cv2.putText(img, "GC12345", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    
    # Run inference
    result, elapse = engine(img)
    
    if result:
        text = result[0][1]
        print(f"✅ Inference Successful!")
        print(f"   Detected Text: '{text}'")
        
        if "12345" in text:
            print("✅ Accuracy Check Passed.")
            print("\n🎉 GREAT NEWS: RapidOCR is working on this Linux system!")
            print("   You can now safely use 'rapidocr_onnxruntime' in your project.")
        else:
            print("⚠️ Accuracy Check Failed (unexpected text).")
    else:
        print("❌ Inference returned no result.")
        
except Exception as e:
    print(f"❌ ERROR: Inference failed (Runtime Error).")
    print("   This is where 'Illegal Instruction' or 'segmentation fault' errors usually appear.")
    print(f"   Error details: {e}")
    sys.exit(1)
