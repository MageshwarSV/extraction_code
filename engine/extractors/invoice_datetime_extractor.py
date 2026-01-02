"""
Format 3 Invoice Date/Time Extractor - JSW Cement
Robust extraction with OCR error handling for smudged labels
"""
import re
from typing import Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def extract_invoice_date_format3(text: str) -> Optional[str]:
    """
    Extract Invoice Date from Format 3 invoices - ROBUST OCR ERROR HANDLING
    
    Format: "Invoice Date/Time    12.12.2025 06:55:38"
    Extracts: "12.12.2025" (date only, without time)
    Pattern: DD.MM.YYYY
    
    OCR Challenges:
    - "Invoice" may be read as "Inv", "Invoce", "Ivoice" (missing parts)
    - "Date" may be read as "Dat", "ate", "Dte"
    - "Time" may be read as "Tim", "ime", "Tme"
    - Slash "/" may be read as "I" or "|" or missing
    
    Strategy:
    1. Search for full pattern "Invoice Date/Time" + datetime (for accuracy)
    2. Extract date portion only (DD.MM.YYYY)
    3. Normalize OCR errors in date value (O→0, I→1, etc.)
    
    Args:
        text: Full OCR text from invoice
        
    Returns:
        Formatted date string "DD.MM.YYYY" or None
    """
    
    if not text:
        return None
    
    # Normalize text
    text_upper = text.upper()
    
    # PRIORITY 1: Exact or near-exact match for "Invoice Date/Time" label
    # Pattern: Invoice Date/Time followed by datetime
    patterns_exact = [
        # Full label variations
        r'INVOICE\s+DATE\s*/\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        r'INVOICE\s+DATE\s*[/|I]\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        r'INVOICE\s+DATE\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
    ]
    
    for pattern in patterns_exact:
        match = re.search(pattern, text_upper)
        if match:
            datetime_str = match.group(1)
            # Normalize and validate
            normalized = _normalize_datetime_ocr(datetime_str)
            if normalized and _validate_datetime(normalized):
                # Extract only date portion (DD.MM.YYYY)
                date_only = normalized.split()[0] if ' ' in normalized else normalized
                logger.info(f"[INVOICE DATE] Extracted (exact pattern): {date_only}")
                return date_only
    
    # PRIORITY 2: Fuzzy pattern - handle missing parts of label
    # Look for partial matches like:
    # - "INV DATE/TIME" (missing "oice")
    # - "INVOICE DAT/TIME" (missing "e")
    # - "INVOICE DATE/TIM" (missing "e")
    patterns_fuzzy = [
        # Missing parts from "Invoice"
        r'INV\w*\s+DATE\s*[/|I]?\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        
        # Missing parts from "Date"
        r'INVOICE\s+D\w*TE?\s*[/|I]?\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        
        # Missing parts from "Time"
        r'INVOICE\s+DATE\s*[/|I]?\s*T\w*ME?\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        
        # Very fuzzy - just need "INV" + "DATE" + datetime pattern
        r'INV\w*\s+D\w*TE?\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
    ]
    
    for pattern in patterns_fuzzy:
        match = re.search(pattern, text_upper)
        if match:
            datetime_str = match.group(1)
            normalized = _normalize_datetime_ocr(datetime_str)
            if normalized and _validate_datetime(normalized):
                # Extract only date portion (DD.MM.YYYY)
                date_only = normalized.split()[0] if ' ' in normalized else normalized
                logger.info(f"[INVOICE DATE] Extracted (fuzzy pattern): {date_only}")
                logger.debug(f"  Matched pattern: {pattern[:60]}...")
                return date_only
    
    # PRIORITY 3: Contextual extraction
    # Look for datetime pattern near "Invoice" or "Date" keywords
    # This handles extreme cases where label is heavily damaged
    lines = text_upper.split('\n')
    for i, line in enumerate(lines):
        # Check if line contains invoice-related keywords
        if re.search(r'INV|INVOICE|DATE|TIME', line):
            # Search for datetime pattern in this line and next few lines
            search_lines = [line] + lines[i+1:min(i+3, len(lines))]
            for search_line in search_lines:
                # Look for DD.MM.YYYY HH:MM:SS pattern
                match = re.search(r'(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})', search_line)
                if match:
                    datetime_str = match.group(1)
                    normalized = _normalize_datetime_ocr(datetime_str)
                    if normalized:
                        # Validate: should be a reasonable date
                        if _validate_datetime(normalized):
                            # Extract only date portion (DD.MM.YYYY)
                            date_only = normalized.split()[0] if ' ' in normalized else normalized
                            logger.info(f"[INVOICE DATE] Extracted (contextual): {date_only}")
                            logger.debug(f"  From line: {line[:60]}")
                            return date_only
    
    logger.warning("[INVOICE DATE] Could not extract Invoice Date/Time")
    return None


def _normalize_datetime_ocr(datetime_str: str) -> Optional[str]:
    """
    Normalize OCR errors in datetime string
    
    Common OCR errors:
    - O (letter) → 0 (digit)
    - I (letter) → 1 (digit)
    - S → 5
    - Spaces in numbers
    
    Examples:
    - "12.12.2O25 O6:55:38" → "12.12.2025 06:55:38"
    - "I2.12.2025 06:5S:38" → "12.12.2025 06:55:38"
    """
    if not datetime_str:
        return None
    
    # Remove extra spaces at start/end
    cleaned = datetime_str.strip()
    
    # Apply OCR corrections
    trans_table = str.maketrans({
        'O': '0',  # Letter O → digit 0
        'o': '0',
        'I': '1',  # Letter I → digit 1
        'l': '1',
        '|': '1',
        'S': '5',  # Letter S → digit 5
        's': '5',
        'B': '8',  # Letter B → digit 8
    })
    
    corrected = cleaned.translate(trans_table)
    
    # Normalize internal whitespace (multiple spaces → single space)
    corrected = re.sub(r'\s+', ' ', corrected)
    
    # Ensure format: DD.MM.YYYY HH:MM:SS
    # Check if we have the basic datetime pattern
    match = re.search(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})', corrected)
    if match:
        day, month, year, hour, minute, second = match.groups()
        # Rebuild with correct format
        formatted = f"{day}.{month}.{year} {hour}:{minute}:{second}"
        return formatted
    
    # If pattern doesn't match, return as-is (will fail validation later)
    return corrected


def _validate_datetime(datetime_str: str) -> bool:
    """
    Validate that datetime string is reasonable
    
    Checks:
    - Date components are valid (day 1-31, month 1-12, year 2020-2030)
    - Time components are valid (hour 0-23, minute/second 0-59)
    """
    try:
        # Parse datetime
        match = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})', datetime_str)
        if not match:
            return False
        
        day, month, year, hour, minute, second = map(int, match.groups())
        
        # Validate ranges
        if not (1 <= day <= 31):
            return False
        if not (1 <= month <= 12):
            return False
        if not (2020 <= year <= 2030):  # Reasonable range for invoices
            return False
        if not (0 <= hour <= 23):
            return False
        if not (0 <= minute <= 59):
            return False
        if not (0 <= second <= 59):
            return False
        
        # Try parsing with datetime to validate full date
        dt = datetime(year, month, day, hour, minute, second)
        return True
        
    except (ValueError, AttributeError):
        return False


def parse_invoice_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parse invoice datetime string to Python datetime object
    
    Args:
        datetime_str: Format "DD.MM.YYYY HH:MM:SS"
        
    Returns:
        datetime object or None
    """
    if not datetime_str:
        return None
    
    try:
        # Parse format: 12.12.2025 06:55:38
        return datetime.strptime(datetime_str, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        logger.warning(f"[INVOICE DATE] Failed to parse datetime: {datetime_str}")
        return None


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")
    
    test_cases = [
        # Perfect case
        ("Invoice Date/Time    12.12.2025 06:55:38", "12.12.2025"),
        
        # OCR errors in label
        ("Inv Date/Time    12.12.2025 06:55:38", "12.12.2025"),  # Missing "oice"
        ("Invoice Dat/Time    12.12.2025 06:55:38", "12.12.2025"),  # Missing "e"
        ("Invoice Date/Tim    12.12.2025 06:55:38", "12.12.2025"),  # Missing "e"
        ("Invoce Date/Time    12.12.2025 06:55:38", "12.12.2025"),  # Missing "i"
        
        # Slash variations
        ("Invoice DateITime    12.12.2025 06:55:38", "12.12.2025"),  # / → I
        ("Invoice Date|Time    12.12.2025 06:55:38", "12.12.2025"),  # / → |
        ("Invoice DateTime    12.12.2025 06:55:38", "12.12.2025"),    # No slash
        
        # OCR errors in datetime value
        ("Invoice Date/Time    I2.12.2025 06:55:38", "12.12.2025"),  # I → 1
        ("Invoice Date/Time    12.12.2O25 06:55:38", "12.12.2025"),  # O → 0
        ("Invoice Date/Time    12.12.2025 O6:55:38", "12.12.2025"),  # O → 0
        ("Invoice Date/Time    12.12.2025 06:5S:38", "12.12.2025"),  # S → 5
        
        # Multiple errors
        ("Inv DatelTime    I2.I2.2O25 O6:5S:38", "12.12.2025"),  # Multiple
        
        # Colon instead of period in date
        ("Invoice Date/Time: 12.12.2025 06:55:38", "12.12.2025"),
        
        # From actual Format 3 document
        ("Invoice / ODN No ™N2533041681\nInvoice Date/Time 12.12.2025 06:55:38", "12.12.2025"),
    ]
    
    print("=" * 80)
    print("TESTING INVOICE DATE/TIME EXTRACTOR")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_text, expected in test_cases:
        result = extract_invoice_date_format3(test_text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"  Input: {test_text[:60]}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
    
    print(f"\n{'=' * 80}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'=' * 80}")
