# engine/extractors/ai_refine_all_fields.py
"""
AI-Powered Field Refinement using OpenAI ChatGPT

This module sends all extracted OCR data to ChatGPT for intelligent validation,
correction, and completion of missing/incorrect fields.

Features:
✅ Validates and corrects all extracted fields (except Delivery Address - handled by delivery_address.py)
✅ Fixes OCR errors in Vehicle Numbers (e.g., TN11BK7553 → TN18K7553)
✅ Completes missing fields based on invoice context
✅ Validates Indian-specific formats (mobile, vehicle plates, E-Way bills)
✅ Smart retry logic with exponential backoff
✅ Fallback to original data if AI fails
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Load .env file if not already loaded
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)  # Don't override if already set
except Exception:
    pass  # dotenv is optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# -------------------------------------
# Optional OpenAI SDK
# -------------------------------------
_HAS_OPENAI = False
openai_client = None
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    OpenAI = None
    _HAS_OPENAI = False

# -------------------------------------
# Configuration from environment
# -------------------------------------
def _get_config():
    """Get AI refinement configuration from environment variables"""
    return {
        'max_retries': int(os.environ.get("OPENAI_MAX_RETRIES", "3")),
        'wait_seconds': float(os.environ.get("OPENAI_WAIT_SECONDS", "2")),
        'backoff_multiplier': float(os.environ.get("OPENAI_BACKOFF_MULTIPLIER", "2.0")),
        'model': os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),  # Cost-effective model
        'temperature': float(os.environ.get("OPENAI_TEMPERATURE", "0.1")),  # Low temp for consistency
    }

# -------------------------------------
# Prompt builder for field refinement
# -------------------------------------
def _build_refinement_prompt(raw_data: Dict[str, Any], full_ocr_text: str) -> str:
    """
    Build a comprehensive prompt for ChatGPT to refine all extracted fields.
    
    The prompt instructs ChatGPT to:
    1. Validate all fields against Indian invoice standards
    2. Correct OCR errors (especially in Vehicle, E-Way Bill, Mobile)
    3. Fill missing fields if inferable from OCR text
    4. Return JSON with corrections and explanations
    """
    
    # Format the raw data for the prompt (exclude internal fields)
    display_data = {k: v for k, v in raw_data.items() 
                   if not k.startswith('_') and k != 'Delivery Address'}
    
    prompt = f"""You are an expert at validating and correcting OCR-extracted data from Indian transport invoices.

**EXTRACTED DATA (from OCR):**
```json
{json.dumps(display_data, indent=2, ensure_ascii=False)}
```

**FULL OCR TEXT (for context):**
```
{full_ocr_text[:3000]}...
```

**YOUR TASK:**
ONLY correct CLEAR OCR errors by checking the FULL OCR TEXT. Be VERY CONSERVATIVE.

**PRIMARY FOCUS - Vehicle Number:**
   - Indian format: XX##XX#### or XX##X#### (e.g., TN18K7553, TN88AA1234)
   - ONLY fix if you can CONFIRM the error in the OCR text
   - Check OCR text carefully: Does it show "88" or "8B"? Use what's in the OCR text
   - DO NOT guess between similar characters (8 vs B, 0 vs O, 1 vs I)
   - If OCR text shows "88", keep "88". If it shows "8B", keep "8B"
   - If you can't find the vehicle number in OCR text, LEAVE AS-IS
   
**Examples:**
   - OCR shows "TN88K7553" → Keep as "TN88K7553" ✓
   - OCR shows "TN8BK7553" → Keep as "TN8BK7553" ✓
   - OCR shows "TN1BK7553" but context suggests district 18 → Fix to "TN18K7553" ✓
   - Can't find in OCR → LEAVE AS-IS ✓

**SECONDARY - Only fix OBVIOUS OCR errors:**
   - E-Way Bill: Only if contains letters instead of all digits
   - Mobile: Only if has wrong digit count or letters mixed in
   - Dates: KEEP AS-IS (don't change years, months, or days)
   - Other fields: LEAVE AS-IS unless obviously corrupted

**CRITICAL RULES:**
- Trust the extracted data - it's already been OCR processed
- DO NOT change dates to "current year" or "logical dates"
- DO NOT change mobile numbers that are valid 10-digit numbers
- DO NOT modify Delivery Address (handled separately)
- When in doubt, LEAVE IT UNCHANGED
- Only correct if you can see the error clearly in the OCR text

**Return ONLY valid JSON:**
```json
{{
  "corrections": {{
    "field_name": {{
      "original": "value",
      "corrected": "fixed_value",
      "reason": "OCR text shows [X] but extracted as [Y]"
    }}
  }},
  "validated_data": {{
    // All fields (changed + unchanged)
  }}
}}
```
- Return ONLY the JSON, no explanation text before/after
"""
    
    return prompt

# -------------------------------------
# AI refinement with retry logic
# -------------------------------------
def refine_extracted_data(
    raw_data: Dict[str, Any],
    full_ocr_text: str,
    *,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send extracted data to ChatGPT for intelligent validation and correction.
    
    Args:
        raw_data: Dictionary of extracted fields
        full_ocr_text: Complete OCR text from invoice
        api_key: OpenAI API key (or from env OPENAI_API_KEY)
    
    Returns:
        Dictionary with:
        {
            "refined": bool,  # Whether AI refinement was applied
            "data": dict,     # Corrected data (or original if AI failed)
            "corrections": dict,  # What was changed
            "error": str      # Error message if failed
        }
    """
    
    # Prepare result structure
    result = {
        "refined": False,
        "data": raw_data.copy(),
        "corrections": {},
        "error": None
    }
    
    # Check if OpenAI is available
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not _HAS_OPENAI:
        logger.warning("OpenAI SDK not installed. Install: pip install openai")
        logger.warning("Skipping AI refinement, returning original data")
        result["error"] = "OpenAI SDK not available"
        return result
    
    if not key:
        logger.warning("OPENAI_API_KEY not found in environment variables")
        logger.warning("Skipping AI refinement, returning original data")
        result["error"] = "API key not configured"
        return result
    
    # Get configuration
    config = _get_config()
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=key)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        result["error"] = f"Client init failed: {e}"
        return result
    
    # Build prompt
    prompt = _build_refinement_prompt(raw_data, full_ocr_text)
    
    # Retry loop
    attempt = 0
    wait = config['wait_seconds']
    
    while attempt < config['max_retries']:
        attempt += 1
        
        try:
            logger.info(f"[AI Refine] Attempt {attempt}/{config['max_retries']}...")
            
            # Call ChatGPT
            response = client.chat.completions.create(
                model=config['model'],
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at validating Indian transport invoice data. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=config['temperature'],
                max_tokens=2000
            )
            
            # Extract response
            ai_response = response.choices[0].message.content.strip()
            logger.debug(f"[AI Refine] Raw response: {ai_response[:200]}...")
            
            # Parse JSON (handle markdown code blocks)
            ai_response = ai_response.strip()
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.startswith("```"):
                ai_response = ai_response[3:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            ai_response = ai_response.strip()
            
            # Parse the JSON
            try:
                ai_result = json.loads(ai_response)
            except json.JSONDecodeError as e:
                logger.warning(f"[AI Refine] JSON parse error: {e}")
                logger.debug(f"[AI Refine] Problematic response: {ai_response[:500]}")
                raise  # Will trigger retry
            
            # Validate response structure
            if not isinstance(ai_result, dict):
                raise ValueError("AI response is not a dictionary")
            
            validated_data = ai_result.get("validated_data", {})
            corrections = ai_result.get("corrections", {})
            
            if not validated_data:
                logger.warning("[AI Refine] No validated_data in response, using original")
                return result
            
            # Success! Update result
            result["refined"] = True
            result["data"] = validated_data
            result["corrections"] = corrections
            
            # Log corrections
            if corrections:
                logger.info("[AI Refine] ✓ Fields corrected:")
                for field, change in corrections.items():
                    logger.info(f"  • {field}: '{change.get('original')}' → '{change.get('corrected')}'")
                    logger.info(f"    Reason: {change.get('reason', 'N/A')}")
            else:
                logger.info("[AI Refine] ✓ All fields validated (no corrections needed)")
            
            return result
        
        except Exception as e:
            logger.warning(f"[AI Refine] Attempt {attempt} failed: {e}")
            result["error"] = str(e)
            
            # If last attempt, return original data
            if attempt >= config['max_retries']:
                logger.error(f"[AI Refine] Max retries ({config['max_retries']}) reached")
                logger.error("[AI Refine] Returning original data without AI refinement")
                return result
            
            # Wait before retry (exponential backoff)
            logger.debug(f"[AI Refine] Waiting {wait:.1f}s before retry...")
            time.sleep(wait)
            wait *= config['backoff_multiplier']
    
    # Fallback (should not reach here)
    return result

# -------------------------------------
# Convenience function for single fields
# -------------------------------------
def validate_vehicle_number(vehicle: Optional[str], ocr_text: str) -> Optional[str]:
    """
    Quick validation/correction of just the vehicle number using ChatGPT.
    Useful for targeted fixes.
    """
    if not vehicle:
        return None
    
    # Simple prompt for vehicle-only validation
    prompt = f"""Fix this Indian vehicle number if it has OCR errors.

Vehicle Number: {vehicle}

Context from invoice:
{ocr_text[:500]}

Common OCR errors:
- "11B" misread as "18" (district code)
- "1B" misread as "18"
- "8" misread as "B" in series letters
- "0" misread as "D" or "O"

Format: STATE(2 letters) + DISTRICT(1-2 digits) + SERIES(1-3 letters) + NUMBER(3-4 digits)
Example: TN18K7553

Return ONLY the corrected vehicle number, nothing else."""
    
    key = os.environ.get("OPENAI_API_KEY")
    if not _HAS_OPENAI or not key:
        return vehicle
    
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You validate Indian vehicle numbers. Return only the corrected number."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        corrected = response.choices[0].message.content.strip()
        
        # Validate it's a proper format
        if re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}$', corrected):
            if corrected != vehicle:
                logger.info(f"[Vehicle Fix] {vehicle} → {corrected}")
            return corrected
        else:
            logger.warning(f"[Vehicle Fix] AI returned invalid format: {corrected}")
            return vehicle
    
    except Exception as e:
        logger.warning(f"[Vehicle Fix] Failed: {e}")
        return vehicle


def refine_consignee(candidate: Optional[str], full_ocr_text: str, *, api_key: Optional[str] = None, min_accept_confidence: float = 0.70) -> Dict[str, Any]:
    """
    Targeted refinement for Consignee field.

    Strategy:
    - Compute a simple heuristic confidence score for the candidate.
    - If score >= min_accept_confidence, accept and return without calling AI.
    - Otherwise, call ChatGPT to extract the most-likely consignee from the full OCR text.
    - The ChatGPT response is expected to return JSON like:
      {"consignee": "AVS Tech Building Solutions I Pvt Ltd.", "confidence": 0.92}

    Returns dict: {"refined": bool, "consignee": str or None, "confidence": float, "error": str or None}
    """
    result = {"refined": False, "consignee": candidate, "confidence": 0.0, "error": None}

    def _heuristic_score(s: Optional[str]) -> float:
        if not s:
            return 0.0
        s_clean = s.strip()
        letters = re.findall(r'[A-Za-z]', s_clean)
        if not letters:
            return 0.0
        alpha_ratio = sum(c.isalpha() for c in s_clean) / (len(re.sub(r'\s+', '', s_clean)) or 1)
        score = alpha_ratio * 0.6
        # boost if contains business keywords
        if re.search(r'\b(LIMITED|LTD|PVT|PRIVATE|AGENCIES|AGENCY|TRADERS|CONSTRUCTION|ENGINEERS|CO\.?|SOLUTIONS|TECH)\b', s_clean, re.IGNORECASE):
            score += 0.25
        # boost for multi-word names
        if len(s_clean.split()) >= 2:
            score += 0.10
        return min(1.0, score)

    # 1) Compute heuristic confidence
    score = _heuristic_score(candidate)
    result["confidence"] = float(score)

    if score >= min_accept_confidence:
        # Good enough, accept candidate
        result["refined"] = False
        result["consignee"] = candidate
        return result

    # 2) If OpenAI SDK not available or no key, skip AI and return candidate
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not _HAS_OPENAI or not key:
        result["error"] = "OpenAI SDK or API key not available"
        return result

    # Build a concise prompt asking the model to extract the consignee/company name
    prompt = f"""
You are given the full OCR text of an invoice. Extract ONLY the consignee/company name (the recipient of the shipment).

Rules:
- Return JSON only, no explanation.
- The JSON must be: {{"consignee": "<company name>", "confidence": <0.0-1.0>}}
- If the model is highly confident, set confidence near 0.9-1.0. If unsure, set lower.
- Prefer complete company names (2-6 words). Avoid returning only suffix tokens like 'Pvt Ltd' or 'LTD'.
- Strip address lines and delivery details; return the company/business name only.
- Do NOT invent companies not present in the OCR.

OCR_TEXT_START
{full_ocr_text[:12000]}
OCR_TEXT_END
"""

    # Call ChatGPT with retry logic similar to refine_extracted_data
    config = _get_config()
    client = None
    try:
        client = OpenAI(api_key=key)
    except Exception as e:
        result["error"] = f"OpenAI init failed: {e}"
        return result

    attempt = 0
    wait = config['wait_seconds']
    while attempt < config['max_retries']:
        attempt += 1
        try:
            resp = client.chat.completions.create(
                model=config['model'],
                messages=[
                    {"role": "system", "content": "You are an expert at extracting company names from noisy OCR text. Return only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=300
            )
            text_resp = resp.choices[0].message.content.strip()
            # strip code fences
            if text_resp.startswith("```json"):
                text_resp = text_resp[7:]
            if text_resp.startswith("```"):
                text_resp = text_resp[3:]
            if text_resp.endswith("```"):
                text_resp = text_resp[:-3]
            text_resp = text_resp.strip()
            try:
                parsed = json.loads(text_resp)
            except Exception:
                # try to recover by extracting a JSON substring
                m = re.search(r'\{[\s\S]*\}', text_resp)
                if m:
                    parsed = json.loads(m.group(0))
                else:
                    raise

            cons = parsed.get('consignee') or parsed.get('Consignee')
            conf = parsed.get('confidence') or parsed.get('confidence_score') or 0.0
            try:
                conf = float(conf)
            except Exception:
                conf = 0.0

            if cons:
                # basic post-validation: avoid suffix-only answers
                def _is_good_company(name: str) -> bool:
                    if not name:
                        return False
                    s = name.strip()
                    # remove punctuation and split
                    words = [w for w in re.split(r"\s+|[,|\\|/]", s) if w.strip()]
                    if len(words) == 0:
                        return False
                    suffixes = {"pvt", "ltd", "private", "limited", "llp", "co", "company", "inc", "corp", "gmbh"}
                    core = [re.sub(r'[^A-Za-z]', '', w).lower() for w in words]
                    # require at least one core word that's not a suffix and length >2
                    if not any((c and (c not in suffixes) and len(c) > 2) for c in core):
                        return False
                    # require at least 2 words or presence of company keyword
                    if len(words) < 2 and not re.search(r'\b(LIMITED|LTD|PVT|PRIVATE|AGENCIES|AGENCY|TRADERS|CONSTRUCTION|ENGINEERS|SOLUTIONS|TECH)\b', s, re.IGNORECASE):
                        return False
                    return True

                cons_clean = cons.strip()
                if not _is_good_company(cons_clean):
                    # AI returned a poor candidate; do not accept
                    result['error'] = 'AI returned unsuitable consignee'
                    result['consignee'] = cons_clean
                    result['confidence'] = float(conf)
                    result['refined'] = False
                    return result

                result['refined'] = True
                result['consignee'] = cons_clean
                result['confidence'] = float(conf)
                return result

            result['error'] = 'AI returned no consignee'
            return result

        except Exception as e:
            result['error'] = str(e)
            time.sleep(wait)
            wait *= config['backoff_multiplier']

    return result

# -------------------------------------
# CLI test
# -------------------------------------
if __name__ == "__main__":
    import sys
    
    # Test with sample data
    sample_data = {
        "Vehicle": "TN11BK7553",  # Wrong - should be TN18K7553
        "E-Way Bill No": "581886878483",
        "Consignment No": "6598",
        "Invoice No": "6978028726",
        "Consignee": "SRI MURUGAN HARDWARES"
    }
    
    sample_ocr = """
    Vehicle No./Wagon NO.: TN11BK7553
    E-Way Bill No: 581886878483
    L.R.No/RR No.: 6598
    Invoice No: 6978028726
    """
    
    print("Testing AI refinement...")
    print("=" * 60)
    
    result = refine_extracted_data(sample_data, sample_ocr)
    
    print("\nRESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
