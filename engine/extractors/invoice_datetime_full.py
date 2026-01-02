"""
Format 3 Invoice DateTime Extractor - FULL DATETIME (with time)
For proper invoice deduplication
"""
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_invoice_datetime_full(text: str) -> Optional[str]:
    """
    Extract FULL Invoice Date/Time from Format 3 invoices (includes time component)
    
    Format: "Invoice Date/Time    12.12.2025 06:55:38"
    Returns: "12.12.2025 06:55:38" (full datetime for deduplication)
    
    This is different from extract_invoice_date_format3 which only returns date.
    Use this for identifying unique invoices.
    """
    
    if not text:
        return None
    
    text_upper = text.upper()
    
    # Pattern: Invoice Date/Time followed by full datetime
    patterns = [
        r'INVOICE\s+DATE\s*/\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        r'INVOICE\s+DATE\s*[/|I]\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
        r'INVOICE\s+DATE\s*TIME\s*[:.\s]+(\d{1,2}[.\s]+\d{1,2}[.\s]+\d{4}\s+\d{1,2}:\d{2}:\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_upper)
        if match:
            datetime_str = match.group(1)
            # Normalize OCR errors
            normalized = _normalize_datetime(datetime_str)
            if normalized:
                logger.info(f"[INVOICE DATETIME] Extracted: {normalized}")
                return normalized
    
    logger.warning("[INVOICE DATETIME] Could not extract full datetime")
    return None


def _normalize_datetime(datetime_str: str) -> Optional[str]:
    """Normalize datetime string with OCR corrections"""
    if not datetime_str:
        return None
    
    cleaned = datetime_str.strip()
    
    # OCR corrections
    trans_table = str.maketrans({
        'O': '0', 'o': '0',
        'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5',
        'B': '8',
    })
    
    corrected = cleaned.translate(trans_table)
    corrected = re.sub(r'\s+', ' ', corrected)
    
    # Extract and format
    match = re.search(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})', corrected)
    if match:
        day, month, year, hour, minute, second = match.groups()
        return f"{day}.{month}.{year} {hour}:{minute}:{second}"
    
    return corrected


# For backward compatibility
if __name__ == "__main__":
    # Test
    test_cases = [
        "Invoice Date/Time    12.12.2025 12:49:17",
        "Invoice Date/Time    12.12.2025 12:49:33",
    ]
    
    for test in test_cases:
        result = extract_invoice_datetime_full(test)
        print(f"{test} → {result}")
