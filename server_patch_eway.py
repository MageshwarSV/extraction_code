"""
[SERVER PATCH]
This script modifies 'engine/extractors/client1_format1.py' to fix the E-Way Bill extraction logic.
It adds a PRIORITY check for the 12-digit number (using direct regex) at the START of 'extract_eway_bill'.
This bypasses the image-based OCR step that fails on Linux/Docker (reading 115... vs 511...).
"""

import os
import re

TARGET_FILE = "engine/extractors/client1_format1.py"

def patch_file():
    if not os.path.exists(TARGET_FILE):
        print(f"❌ Error: File {TARGET_FILE} not found!")
        return

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already patched
    if "Priority: Direct Regex Search" in content:
        print("✅ File is already patched. Skipping.")
        return

    print(f"Read {len(content)} bytes from {TARGET_FILE}")

    # The function signature to find
    func_sig = "def extract_eway_bill(text: str, ocr_images: list = None, pdf_path: str = None) -> str:"
    
    # The new logic to insert at the beginning of the function
    new_logic = """    # --- Priority: Direct Regex Search (Fix for Docker/Linux 115... vs 511... issue) ---
    # Attempt to find the 12-digit number DIRECTLY in the full text first.
    # This avoids image-based rendering differences in Poppler between Windows/Linux.
    if text:
        # Find all 12-digit numbers
        candidates = re.findall(r'\\b([0-9]{12})\\b', text)
        for cand in candidates:
            # Basic validation: It must be numeric and length 12 (regex ensures this)
            
            # Context validation: Check if 'E-Way' or 'EWay' is near this candidate in the original text
            # We assume the text has newlines. We check the line containing the candidate.
            for line in text.splitlines():
                if cand in line:
                    # Normalized line check
                    norm_line = line.lower().replace(" ", "")
                    # Keywords: eway, e-way, bill
                    if "eway" in norm_line or "bill" in norm_line:
                        print(f"[E-Way Fix] Found high-confidence E-Way Bill via text: {cand}")
                        return cand
            
            # If we just found a stray 12-digit number but it starts with 5 (common for this client), take it
            # This is a fallback heuristic if context is missing/messy
            if cand.startswith("5"):
                 print(f"[E-Way Fix] Found likely E-Way Bill by format: {cand}")
                 return cand

    # ---------------------------------------------------------------------------------------
"""

    if func_sig in content:
        # Replace the signature with signature + new logic
        new_content = content.replace(func_sig, func_sig + "\n" + new_logic)
        
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✅ Successfully patched extract_eway_bill in client1_format1.py")
    else:
        # Try finding it without type hints just in case
        func_sig_simple = "def extract_eway_bill(text, ocr_images=None, pdf_path=None):"
        if func_sig_simple in content:
             new_content = content.replace(func_sig_simple, func_sig_simple + "\n" + new_logic)
             with open(TARGET_FILE, "w", encoding="utf-8") as f:
                f.write(new_content)
             print("✅ Successfully patched extract_eway_bill (simple sig) in client1_format1.py")
        else:
            print("❌ Could not find 'extract_eway_bill' function definition. Patch failed.")

if __name__ == "__main__":
    patch_file()
