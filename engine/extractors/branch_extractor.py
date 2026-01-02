"""
Format 3 Branch/Source Extractor - POST Location Extraction
Handles OCR errors where POST may be read as OST, PT, PS, ST
Includes FUZZY MATCHING to correct OCR-damaged location names
"""
import re
from typing import Optional, List, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

# Known JSW Cement branch locations for fuzzy matching
# Add more branches as needed
KNOWN_BRANCHES = [
    "POTTANERI",
    "SALEM",
    "METTUR",
    "NANDYAL",
    "VIJAPUR",
    "SALBONI",
    "JAJPUR",
    "DOLVI",
]


def fuzzy_match_branch(extracted: str, threshold: float = 0.75) -> Optional[str]:
    """
    Use fuzzy matching to correct OCR-damaged branch names
    
    Examples:
    - "POTTANER" → "POTTANERI" (90% match)
    - "POTTANERI" → "POTTANERI" (100% exact match)
    - "POTTANER1" → "POTTANERI" (90% match, 1 instead of I)
    - "P0TTANERI" → "POTTANERI" (90% match, 0 instead of O)
    
    Args:
        extracted: The OCR-extracted location name
        threshold: Minimum similarity (0.0 to 1.0). Default 0.75 = 75%
        
    Returns:
        Corrected branch name if match found, or original if above threshold
    """
    if not extracted:
        return None
    
    extracted_upper = extracted.upper().strip()
    
    # First check for exact match
    if extracted_upper in KNOWN_BRANCHES:
        logger.debug(f"[FUZZY] Exact match found: {extracted_upper}")
        return extracted_upper
    
    # Find best fuzzy match
    best_match = None
    best_ratio = 0.0
    
    for known_branch in KNOWN_BRANCHES:
        # Use SequenceMatcher for similarity ratio
        ratio = SequenceMatcher(None, extracted_upper, known_branch).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = known_branch
    
    # Return corrected name if similarity is above threshold
    if best_ratio >= threshold:
        if extracted_upper != best_match:
            logger.info(f"[FUZZY] Auto-corrected: '{extracted}' → '{best_match}' (similarity: {best_ratio:.1%})")
        return best_match
    
    # If below threshold, return original (might be a new branch)
    logger.warning(f"[FUZZY] No good match for '{extracted}' (best: {best_match} at {best_ratio:.1%})")
    return extracted_upper


def extract_branch_from_post(text: str) -> Optional[str]:
    """
    Extract branch/source location from POST field - ROBUST OCR ERROR HANDLING
    
    Format 3 invoices have: "POST: POTTANERI, TK: METTUR"
    
    OCR Challenges:
    - "POST" may be read as "OST" (P smudged)
    - "POST" may be read as "PT", "PS", "ST" (partial loss)
    - Colon may be missing or replaced with period/space
    
    Strategy:
    1. Look for exact "POST:" pattern first
    2. Fallback to partial patterns (OST:, PT:, PS:, ST:)
    3. Extract word immediately after the pattern
    4. Clean and validate the extracted location
    
    Args:
        text: Full OCR text from invoice
        
    Returns:
        Branch location (e.g., "POTTANERI") or None
    """
    
    if not text:
        return None
    
    # Normalize text for better matching
    text_upper = text.upper()
    
    # PRIORITY 1: Exact match for "POST:" or "POST."
    # Pattern: POST followed by colon/period/space, then capture next word
    patterns_exact = [
        r'\bPOST\s*[:.\s]\s*([A-Z][A-Z]+)',  # POST: POTTANERI
        r'\bPOST\s*[:.\s]\s*(\w+)',          # POST POTTANERI (more flexible)
    ]
    
    for pattern in patterns_exact:
        match = re.search(pattern, text_upper)
        if match:
            location = match.group(1).strip()
            # Validate: should be at least 4 characters (avoid noise like "TK", "NO")
            if len(location) >= 4 and location.isalpha():
                logger.info(f"[BRANCH] Extracted from exact POST pattern: {location}")
                return location
    
    # PRIORITY 2: Fuzzy match for OCR errors
    # Handle cases where P is smudged: "OST:", "OT:", etc.
    patterns_fuzzy = [
        r'\bOST\s*[:.\s]\s*([A-Z][A-Z]+)',   # OST: POTTANERI (P missing)
        r'\bPT\s*[:.\s]\s*([A-Z][A-Z]+)',    # PT: POTTANERI (OS missing)
        r'\bPS\s*[:.\s]\s*([A-Z][A-Z]+)',    # PS: POTTANERI (OT missing)
        r'\bST\s*[:.\s]\s*([A-Z][A-Z]+)',    # ST: POTTANERI (PO missing)
        r'\bOT\s*[:.\s]\s*([A-Z][A-Z]+)',    # OT: POTTANERI (PS missing)
    ]
    
    for pattern in patterns_fuzzy:
        match = re.search(pattern, text_upper)
        if match:
            location = match.group(1).strip()
            # Extra validation for fuzzy matches
            # Check if location looks like a place name (alphabetic, reasonable length)
            if 4 <= len(location) <= 20 and location.isalpha():
                # Additional check: should not be common abbreviations
                if location not in ['METTUR', 'SALEM', 'TAMIL', 'NADU', 'INDIA']:
                    # Verify by checking if "TK:" appears nearby (common pattern)
                    # "POST: POTTANERI, TK: METTUR"
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text_upper), match.end() + 50)
                    context = text_upper[context_start:context_end]
                    
                    # If we see "TK:" or "TALUK" nearby, this is likely correct
                    if re.search(r'\bTK\s*[:.\s]', context) or 'TALUK' in context:
                        logger.info(f"[BRANCH] Extracted from fuzzy POST pattern: {location}")
                        logger.debug(f"  Pattern matched: {pattern}")
                        logger.debug(f"  Context: {context}")
                        return location
    
    # PRIORITY 3: Contextual extraction
    # Look for pattern: "POST: <LOCATION>, TK: <TALUK>"
    # Sometimes OCR splits this across lines
    lines = text_upper.split('\n')
    for i, line in enumerate(lines):
        # Check if line contains POST-like pattern
        if re.search(r'OST|^PT\b|^PS\b|^ST\b', line):
            # Look for comma-separated location before TK
            # Example: "POTTANERI, TK: METTUR"
            match = re.search(r'\b([A-Z]{4,20})\s*,\s*TK\s*[:.\s]', line)
            if match:
                location = match.group(1).strip()
                if location.isalpha():
                    logger.info(f"[BRANCH] Extracted from contextual pattern: {location}")
                    return location
    
    # PRIORITY 4: Last resort - look for location name in address section
    # JSW invoices typically have: "POST: POTTANERI, TK: METTUR"
    # Try to find this pattern even without POST keyword
    match = re.search(r'\b([A-Z]{5,20})\s*,\s*TK\s*[:.\s]\s*([A-Z]+)', text_upper)
    if match:
        location = match.group(1).strip()
        taluk = match.group(2).strip()
        # Validate: location should not be same as taluk
        if location != taluk and location.isalpha():
            logger.info(f"[BRANCH] Extracted from address pattern: {location}")
            logger.debug(f"  Taluk reference: {taluk}")
            return location
    
    logger.warning("[BRANCH] Could not extract POST location from text")
    return None


def extract_branch_refined(text: str, fuzzy_threshold: float = 0.75) -> Optional[str]:
    """
    Enhanced version with fuzzy matching and OCR corrections
    
    This version adds:
    - Fuzzy matching to correct OCR-damaged names (POTTANER → POTTANERI)
    - Common OCR error corrections specific to place names
    - Validation against known location patterns
    
    Args:
        text: Full OCR text from invoice
        fuzzy_threshold: Minimum similarity for fuzzy match (0.75 = 75%)
        
    Returns:
        Corrected branch name or None
    """
    
    # First try main extractor
    branch = extract_branch_from_post(text)
    
    if branch:
        # Apply fuzzy matching to correct OCR errors
        corrected_branch = fuzzy_match_branch(branch, threshold=fuzzy_threshold)
        
        if corrected_branch and corrected_branch != branch:
            logger.info(f"[BRANCH] Fuzzy match applied: {branch} → {corrected_branch}")
        
        return corrected_branch
    
    return None


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")
    
    # Test cases with various OCR errors
    test_cases = [
        # Perfect case
        ("POST: POTTANERI, TK: METTUR", "POTTANERI"),
        
        # Missing P
        ("OST: POTTANERI, TK: METTUR", "POTTANERI"),
        
        # Partial matches
        ("PT: POTTANERI, TK: METTUR", "POTTANERI"),
        ("PS: POTTANERI, TK: METTUR", "POTTANERI"),
        ("ST: POTTANERI, TK: METTUR", "POTTANERI"),
        
        # Period instead of colon
        ("POST. POTTANERI, TK: METTUR", "POTTANERI"),
        
        # No punctuation
        ("POST POTTANERI TK METTUR", "POTTANERI"),
        
        # ⭐ FUZZY MATCHING - OCR errors in location name
        ("POST: POTTANER, TK: METTUR", "POTTANERI"),   # Missing I at end
        ("POST: POTTANER1, TK: METTUR", "POTTANERI"),  # 1 instead of I
        ("POST: P0TTANERI, TK: METTUR", "POTTANERI"),  # 0 instead of O
        ("POST: POTTANER!, TK: METTUR", "POTTANERI"),  # ! instead of I
        ("POST: POTTANERII, TK: METTUR", "POTTANERI"), # Extra I
        ("POST: POTANERI, TK: METTUR", "POTTANERI"),   # Missing T
        ("POST: POTTANER1, TK: MET7UR", "POTTANERI"),  # Multiple errors
        
        # Test other branches with fuzzy match
        ("POST: SALE, TK: METTUR", "SALEM"),           # Missing M
        ("POST: METFUR, TK: SALEM", "METTUR"),         # F instead of T
        
        # Multi-line (common in scanned docs)
        ("JSW CEMENT\nPOST: POTTANERI\nTK: METTUR\nSALEM", "POTTANERI"),
        
        # Edge case: POTTANER without TK reference
        ("POST: POTTANER", "POTTANERI"),  # Should still fuzzy match
    ]
    
    print("=" * 80)
    print("TESTING BRANCH EXTRACTOR")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_text, expected in test_cases:
        result = extract_branch_refined(test_text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"  Input: {test_text[:50]}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
    
    print(f"\n{'=' * 80}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'=' * 80}")
