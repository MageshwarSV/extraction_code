# engine/extractors/ai.py
"""
Self-Learning AI Address Normalizer (No hardcoded places)

✅ Removes: Name&, Name & Address of Delivery, dates, junk
✅ Preserves: acronyms, dotted initials (K.R.KANNAPPA)
✅ Auto-corrects places using pattern-based + AI understanding
✅ Offline: merges "parvath puram" → "Parvathpuram"
✅ AI mode: uses ChatGPT to infer correct Indian localities
✅ Adaptive: learns new place corrections dynamically (places_learned.json)
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Optional, Set

# Load .env file if not already loaded
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
except Exception:
    pass

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
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    OpenAI = None
    _HAS_OPENAI = False

# -------------------------------------
# Regex constants
# -------------------------------------
_HDR_NOISE_RE = re.compile(
    r'\b(?:Name\s*&\s*Address|Name&Address|Name\s*and\s*Address|Name\s*&|Name&|'
    r'Address\s*of\s*(?:Delivery|Recipient|Consignee)|ofDelivery|Deliver\s*to|Ship\s*to)\b',
    flags=re.IGNORECASE
)
_INITIALS_DOTTED_RE = re.compile(r'\b(?:[A-Z]\.){1,}[A-Z0-9]*\b')
_ACRONYM_RE = re.compile(r'\b[A-Z]{2,}\b')
_DATE_LIKE_RE = re.compile(
    r'\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2})\b'
)
_TRAILING_JUNK_RE = re.compile(r'[\!\]\[\?\*#@]+$')

# -------------------------------------
# Persistent learning file
# -------------------------------------
LEARNED_FILE = os.path.join(os.path.dirname(__file__), "places_learned.json")

def _load_learned_places():
    try:
        if os.path.exists(LEARNED_FILE):
            with open(LEARNED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.debug("Could not load learned places file; starting empty.")
    return {}

def _save_learned_places(data: dict):
    try:
        with open(LEARNED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.warning("Failed to save learned places to %s", LEARNED_FILE)

_LEARNED_PLACES = _load_learned_places()

# -------------------------------------
# Helpers
# -------------------------------------
def _strip_header_like_noise(s: str) -> str:
    if not s:
        return s
    s = re.sub(r'([A-Za-z])&([A-Za-z])', r'\1 & \2', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = _HDR_NOISE_RE.sub('', s)
    s = re.sub(r'[,;:\-]{2,}', ',', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip(' ,;:-')

def _extract_acronyms_and_initials(s: str) -> Set[str]:
    if not s:
        return set()
    out = set(_ACRONYM_RE.findall(s))
    out.update(_INITIALS_DOTTED_RE.findall(s))
    return {t.strip(' ,;:-') for t in out if t}

def _remove_date_tokens(s: str) -> str:
    if not s:
        return s
    s = _DATE_LIKE_RE.sub('', s)
    s = re.sub(r'\s{2,}', ' ', s)
    s = re.sub(r'\s*,\s*,+', ', ', s)
    return s.strip(' ,;:-')

def _normalize_token(tok: str) -> str:
    tok = re.sub(r'[^A-Za-z0-9\.\-/&, ]+', '', tok)
    return tok.strip()

# -------------------------------------
# Local pattern-based place correction
# -------------------------------------
def _smart_place_guess(s: str) -> str:
    """
    Offline rule-based guesser for Indian localities.
    Merges & corrects likely place fragments (puram, nagar, pet, malai, etc.)
    """
    if not s:
        return s
    s = s.lower()
    # Merge typical Tamil patterns: puram/nagar/malai/pet/etc.
    s = re.sub(r'\b([a-z]{3,})\s+(puram)\b', r'\1\2', s)
    s = re.sub(r'\b([a-z]{3,})\s+(nagar)\b', r'\1\2', s)
    s = re.sub(r'\b([a-z]{3,})\s+(malai)\b', r'\1\2', s)
    s = re.sub(r'\b([a-z]{3,})\s+(pet)\b', r'\1\2', s)
    s = re.sub(r'\bv\.\s*([a-z]{3,})', r'v\1', s)
    # Apply learned corrections
    for wrong, correct in _LEARNED_PLACES.items():
        try:
            s = re.sub(r'\b' + re.escape(wrong.lower()) + r'\b', correct.lower(), s)
        except Exception:
            continue
    return s

def _capitalize_localities(s: str) -> str:
    """Capitalize each locality word properly."""
    return " ".join(w.capitalize() for w in s.split())

# -------------------------------------
# Local fallback cleanup (offline)
# -------------------------------------
def _simple_local_cleanup(raw: str, preserve: Optional[Set[str]] = None) -> str:
    if not raw:
        return ""
    preserve = preserve or set()
    s = _strip_header_like_noise(raw)
    s = " ".join(s.splitlines()).strip().lower()
    s = _smart_place_guess(s)
    tokens = re.split(r'(\s+|,)', s)
    tokens = [t for t in tokens if t.strip()]
    merged = []

    i = 0
    while i < len(tokens):
        cur = tokens[i]
        if cur == ',':
            merged.append(',')
            i += 1
            continue
        if cur in preserve:
            merged.append(cur)
            i += 1
            continue
        if _DATE_LIKE_RE.fullmatch(cur):
            i += 1
            continue
        merged.append(cur)
        i += 1

    out = " ".join(merged)
    out = re.sub(r'\s*,\s*', ', ', out)
    out = _remove_date_tokens(out)
    out = _smart_place_guess(out)
    out = _TRAILING_JUNK_RE.sub('', out).strip()
    out = re.sub(r'\s{2,}', ' ', out)
    return _capitalize_localities(out.strip(' ,;:-'))

# -------------------------------------
# AI prompt builder
# -------------------------------------
def _build_prompt_for_merge(raw_address: str) -> str:
    return (
        "You are an Indian address corrector.\n"
        "Input is an OCR-extracted delivery address.\n"
        "Return exactly ONE corrected, single-line address.\n\n"
        "Rules:\n"
        " - Remove 'Name&', 'Name & Address', 'ofDelivery', and date-like tokens.\n"
        " - Preserve initials like K.R.KANNAPPA.\n"
        " - Fix broken or split locality names (e.g. 'parvath puram' -> 'Parvathpuram').\n"
        " - Correct misread Indian localities (e.g. 'v.alasaravakkam' -> 'Valsaravakkam') using real map knowledge.\n"
        " - Fix common OCR errors: V↔Y confusion (e.g., 'T.Y.K' -> 'T.V.K', 'Yalasaravakkam' -> 'Valasaravakkam').\n"
        " - Keep commas between localities.\n"
        " - Output ONLY the corrected address, nothing else.\n\n"
        f"Input: {raw_address.strip()}\n\n"
        "Corrected address:"
    )

# -------------------------------------
# AI formatting with retries + waiting
# -------------------------------------
def format_address(prompt_or_raw: str, *, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> str:
    """
    Try AI (ChatGPT) formatting with configurable retries and waiting.
    Falls back to local offline cleanup if AI not available or fails.

    Configurable via environment variables:
      OPENAI_API_KEY        -> API key (required)
      OPENAI_MODEL          -> model name (default: gpt-4o-mini)
      OPENAI_MAX_RETRIES    -> int (default 3)
      OPENAI_WAIT_SECONDS   -> int/float (default 2)
      OPENAI_BACKOFF_MULTIPLIER -> float multiplier for incremental backoff (default 2.0)
      OPENAI_TEMPERATURE    -> float (default 0.1)
    """
    raw_input = (prompt_or_raw or "").strip()
    if not raw_input:
        return ""

    preserve = _extract_acronyms_and_initials(raw_input)
    local_fallback = _simple_local_cleanup(raw_input, preserve)

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not _HAS_OPENAI or not key:
        logger.debug("OpenAI not available or API key missing -> using offline fallback.")
        return local_fallback

    # Read retry settings from environment (allow runtime tweaks)
    try:
        MAX_RETRIES = int(os.environ.get("OPENAI_MAX_RETRIES", "3"))
    except Exception:
        MAX_RETRIES = 3
    try:
        WAIT_SECONDS = float(os.environ.get("OPENAI_WAIT_SECONDS", "2"))
    except Exception:
        WAIT_SECONDS = 2.0
    try:
        BACKOFF_MULTIPLIER = float(os.environ.get("OPENAI_BACKOFF_MULTIPLIER", "2.0"))
    except Exception:
        BACKOFF_MULTIPLIER = 2.0
    try:
        TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.1"))
    except Exception:
        TEMPERATURE = 0.1

    # Override model from environment if set
    model = os.environ.get("OPENAI_MODEL", model)

    prompt = _build_prompt_for_merge(raw_input)

    # init client
    try:
        client = OpenAI(api_key=key)
    except Exception as e:
        logger.warning("OpenAI client initialization failed (%s) -> fallback", e)
        return local_fallback

    attempt = 0
    wait = WAIT_SECONDS
    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            logger.info("AI formatting attempt %d/%d...", attempt, MAX_RETRIES)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert Indian address formatter. Output only the corrected address, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=200
            )
            
            out = response.choices[0].message.content.strip() if response.choices else ""

            if out:
                logger.info("AI returned: %s", out)
                return out

            logger.warning("AI returned empty string on attempt %d", attempt)

        except Exception as e:
            # log exception but do not raise; retry
            logger.warning("AI formatting failed on attempt %d: %s", attempt, e)

        # If last attempt -> fallback
        if attempt >= MAX_RETRIES:
            logger.warning("Max AI attempts (%d) reached -> falling back to offline cleanup", MAX_RETRIES)
            return local_fallback

        # wait (simple backoff)
        try:
            logger.debug("Waiting %.2fs before next AI attempt...", wait)
            time.sleep(wait)
        except Exception:
            pass
        wait = wait * BACKOFF_MULTIPLIER if BACKOFF_MULTIPLIER and BACKOFF_MULTIPLIER > 0 else wait

    # default fallback
    return local_fallback

# -------------------------------------
# Adaptive learning API
# -------------------------------------
def learn_place(wrong: str, correct: str):
    """Store a new learned place correction."""
    wrong = (wrong or "").strip().lower()
    correct = (correct or "").strip().title()
    if not wrong or not correct:
        return
    _LEARNED_PLACES[wrong] = correct
    _save_learned_places(_LEARNED_PLACES)
    logger.info("Learned correction: %s -> %s", wrong, correct)

# -------------------------------------
# CLI test
# -------------------------------------
if __name__ == "__main__":
    import sys
    sample = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()
    key = os.environ.get("OPENAI_API_KEY")
    print(format_address(sample, api_key=key))
