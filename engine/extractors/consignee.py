"""Helper to salvage low-information consignee lines using heuristics and optional AI.

This module exposes `salvage_consignee(full_text: str) -> Optional[str]` which
scans the OCR text for lines that were likely rejected due to low alpha ratio
or embedded codes and attempts to clean them. If an AI refiner is available
(engine.extractors.ai_refine_all_fields.refine_consignee) it will be used
conservatively; otherwise a heuristic cleaner will run locally.
"""
from typing import Optional
import os
import re
import logging
import json
import time

logger = logging.getLogger(__name__)

# Try to use existing AI refiner if available
_HAS_AI = False
_AI_REFINER = None
try:
    from engine.extractors.ai_refine_all_fields import refine_consignee
    _HAS_AI = True
    _AI_REFINER = refine_consignee
except Exception:
    _HAS_AI = False
    _AI_REFINER = None

# Prefer direct OpenAI usage if API key present; keep a safe fallback to existing refiner
_OPENAI_AVAILABLE = False
try:
    import openai
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False


def _simple_cleanup(candidate: str) -> Optional[str]:
    """Simple local cleanup: strip tokens with digits/code-like tokens,
    preserve alphabetic phrases and common suffixes like 'Pvt Ltd'."""
    if not candidate or not candidate.strip():
        return None
    s = candidate.strip()

    # Remove very long sequences of non-alpha characters
    s = re.sub(r'[=*_]{2,}', ' ', s)

    # Tokenize by spaces and punctuation and keep tokens that contain letters
    tokens = re.split(r'[\s,|/\\]+', s)
    kept = []
    for t in tokens:
        # remove surrounding punctuation
        tstr = re.sub(r'^[^A-Za-z]+|[^A-Za-z]+$', '', t)
        if not tstr:
            continue
        # drop tokens that look like dates/codes (contain digits or long runs of punctuation)
        if re.search(r'\d', tstr):
            # allow common suffix tokens even if they contain punctuation (e.g., "Pvt Ltd")
            if re.search(r'(?i)PVT|LTD|PRIVATE|LIMITED|LLP|INC|CO', tstr):
                kept.append(tstr)
            else:
                continue
        else:
            # drop tokens that are single non-informative chars like 'I' when isolated near code
            if len(tstr) == 1 and tstr.isalpha():
                # preserve initials if there are multiple initials nearby; otherwise keep
                kept.append(tstr)
            else:
                kept.append(tstr)

    if not kept:
        return None

    candidate_clean = ' '.join(kept)
    candidate_clean = re.sub(r'\s{2,}', ' ', candidate_clean).strip(' ,:-.')

    # Validate: must have some letters and reasonable length
    letters = re.findall(r'[A-Za-z]', candidate_clean)
    if not letters or len(''.join(letters)) < 3:
        return None

    # Post-process: remove unwanted short uppercase acronyms (codes like 'IPL', 'HSR')
    def _post_clean_name(s: str) -> str:
        if not s:
            return s
        whitelist = {'LLP', 'LTD', 'PVT', 'PVT.', 'CO', 'INC', 'PLC', 'GST', 'PAN'}
        parts = s.split()
        cleaned_parts = []
        for i, p in enumerate(parts):
            up = p.upper()
            if up in whitelist:
                cleaned_parts.append(p)
                continue
            # Remove tokens that are 2-4 uppercase letters (likely codes) unless
            # they appear next to a descriptive token (e.g., 'AVS Tech' -> keep 'AVS')
            if re.fullmatch(r'[A-Z]{2,4}', p):
                next_tok = parts[i+1] if i+1 < len(parts) else None
                prev_tok = parts[i-1] if i-1 >= 0 else None
                keep_flag = False
                if next_tok and re.search(r'[a-z]', next_tok):
                    keep_flag = True
                if prev_tok and re.search(r'[a-z]', prev_tok):
                    keep_flag = True
                if next_tok and len(next_tok) > 3:
                    keep_flag = True
                if prev_tok and len(prev_tok) > 3:
                    keep_flag = True
                if keep_flag:
                    cleaned_parts.append(p)
                    continue
                else:
                    continue
            # Also remove tokens that are slash-joined short codes
            if re.fullmatch(r'(?:[A-Z]{1,4}[/\\-])+(?:[A-Z]{1,4})', p):
                continue
            cleaned_parts.append(p)
        out = ' '.join(cleaned_parts)
        out = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", out, flags=re.IGNORECASE)
        out = re.sub(r'\s{2,}', ' ', out).strip(' ,.-')

        # Remove large duplicated multi-word subsequences (keep the later occurrence)
        def _remove_duplicated_subseq(text: str) -> str:
            words = text.split()
            n = len(words)
            max_w = min(8, n)
            for w in range(max_w, 2, -1):
                for i in range(0, n - w + 1):
                    seq = ' '.join(words[i:i+w])
                    rest = ' '.join(words[i+w:])
                    if seq.lower() in rest.lower():
                        new_words = words[:i] + words[i+w:]
                        return ' '.join(new_words)
            return text

        out = _remove_duplicated_subseq(out)
        return out

    return _post_clean_name(candidate_clean)


def salvage_consignee(full_text: str) -> Optional[str]:
    """Attempt to salvage a consignee from `full_text`.

    1. Look for lines that were likely rejected (contain letters but embedded codes/dates).
    2. Run simple local cleanup to strip code-like tokens.
    3. If AI is available, try AI refinement and accept only if refined or confidence >= threshold.
    """
    # Quick guard
    if not full_text:
        return None

    # configurable acceptance confidence for AI
    try:
        accept_conf = float(os.getenv('CONSIGNEE_ACCEPT_CONFIDENCE', '0.75'))
    except Exception:
        accept_conf = 0.75

    # Candidate selection: lines with letters but low alpha ratio or many slashes
    candidates = []
    lines = (full_text or "").splitlines()
    for idx, ln in enumerate(lines):
        t = (ln or '').strip()
        if not t:
            continue
        # Skip lines that are clearly payment/terms statements
        if re.search(r'(?i)(\bfreight\b.*|freight on this invoice|payable by)', t):
            continue
        # must contain at least one letter
        if not re.search(r'[A-Za-z]', t):
            continue
        # compute alpha ratio over visible chars
        total_vis = len(re.sub(r'\s+', '', t)) or 1
        alpha_ratio = sum(1 for c in t if c.isalpha()) / total_vis
        # pick lines that are borderline (rejected earlier) or contain slashes and codes
        if alpha_ratio < 0.7 or re.search(r'[\d]{2,}|/', t):
            candidates.append((alpha_ratio, t, idx))

    # sort by alpha_ratio descending (prefer more alpha-heavy borderline candidates)
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Try heuristic cleanup first on each candidate
    for _, cand, _ in candidates:
        cleaned = _simple_cleanup(cand)
        if cleaned:
            logger.info(f"[CONSIGNEE.SALVAGE] Heuristic cleaned: '{cand}' -> '{cleaned}'")
            # quick validation: ensure cleaned has >50% alpha ratio
            tv = len(re.sub(r'\s+', '', cleaned)) or 1
            ar = sum(1 for c in cleaned if c.isalpha()) / tv
            if ar >= 0.5 and len(re.sub(r'\s+', '', cleaned)) >= 4:
                return cleaned

    # If OpenAI API key present, prefer calling GPT directly on the top candidate.
    # The user asked to take the highest low-alpha candidate to AI for cleanup.
    if candidates:
        top_alpha, top_candidate, top_idx = candidates[0]

        # Pre-sanitize the candidate to remove payment phrases, dates and slash-codes
        def _pre_sanitize_candidate(candidate_text: str) -> str:
            """Sanitize noisy OCR fragments before calling AI.

            Goals:
            - Remove payment/terms phrases (e.g., 'Freight on this Invoice is payable by ...').
            - Strip long slash/code/date sequences that confuse alpha-ratio.
            - Preserve initials and short legitimate uppercase tokens when adjacent to words.
            """
            if not candidate_text:
                return candidate_text

            s = candidate_text
            # Remove well-known payment/terms phrases (case-insensitive)
            s = re.sub(r"(?i)freight on this invoice.*", "", s)
            s = re.sub(r"(?i)freight (charges|paid|payable|on this invoice).*", "", s)
            s = re.sub(r"(?i)place of supply.*", "", s)
            s = re.sub(r"(?i)pan\s*no[:\.]?\s*\w+", "", s)
            s = re.sub(r"(?i)gst[in]?[:\.]?\s*[A-Z0-9]+", "", s)
            s = re.sub(r"(?i)payment.*", "", s)

            # Remove long slash-joined codes and adjacent date-like tokens
            s = re.sub(r"\b[A-Z]{1,5}(?:/[A-Z0-9\-\.]+){1,}\b", "", s)
            s = re.sub(r"\b\d{1,2}[\-\./]\d{1,2}[\-\./]\d{2,4}\b", "", s)

            # Remove stray sequences of digits or mixed alnum tokens that are not name-like
            s = re.sub(r"\b\d{2,}\b", "", s)

            # Collapse multiple spaces and strip
            s = re.sub(r"\s{2,}", " ", s).strip(' ,.-|')

            # Keep the fragment reasonably short: cut off extremely long fragments to first 12 words
            words = s.split()
            if len(words) > 12:
                s = ' '.join(words[:12])

            return s

        def _call_gpt_for_candidate(candidate_text: str) -> Optional[dict]:
            """Call OpenAI ChatCompletion (Chat API) to clean the company name.

            Returns a dict: {'consignee': str, 'confidence': float, 'refined': bool}
            or None on failure.
            """
            if not _OPENAI_AVAILABLE:
                return None

            api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_APIKEY') or os.getenv('OPENAI_KEY')
            if not api_key:
                logger.info('[CONSIGNEE.SALVAGE] No OpenAI API key in environment')
                return None

            openai.api_key = api_key
            model = os.getenv('CONSIGNEE_GPT_MODEL', os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'))

            # Pre-sanitize candidate text to remove non-name content that confuses GPT
            candidate_text_s = _pre_sanitize_candidate(candidate_text)

            prompt = (
                "You are a careful extractor that returns a concise, cleaned company name from a noisy OCR fragment."
                " Output ONLY a JSON object with keys: 'consignee' (string or null), 'confidence' (0-1 float), and 'refined' (true/false)."
                " Be conservative: do not invent new company names. Preserve initials and multi-word names exactly when reasonable."
                " Remove embedded dates, codes, long slash-delimited references (e.g., IPL/HSR/2526/108/25.10.2025), and surrounding garbage like 'Place of Supply' or 'PAN No'."
                " If the OCR fragment contains an explicit company suffix such as 'Pvt', 'Pvt Ltd', 'Private Limited', 'Ltd', or 'LLP', try to preserve it in the returned 'consignee' (normalize to 'Pvt Ltd' or 'Private Limited' as appropriate)."
                " The 'consignee' output should be short (ideally <= 6 words), normalized (no duplicated phrases), and contain only the company name and suffix."
                " If uncertain, return 'consignee': null and 'confidence': 0.0 and 'refined': false."
                "\n\nOCR fragment (sanitized):\n" + candidate_text_s + "\n\nRespond only with valid JSON (no extra text)."
            )

            try:
                # Use chat completions interface
                resp = openai.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "system", "content": "You extract cleaned company names."},
                              {"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=300,
                )
                text = resp['choices'][0]['message']['content'].strip()
                # Attempt to parse JSON substring
                # Find the first { ... }
                start = text.find('{')
                end = text.rfind('}')
                if start == -1 or end == -1:
                    logger.info('[CONSIGNEE.SALVAGE] GPT returned non-JSON response')
                    return None
                jtxt = text[start:end+1]
                parsed = json.loads(jtxt)
                # normalize keys
                name = parsed.get('consignee') or parsed.get('name') or parsed.get('company')
                conf = float(parsed.get('confidence') or parsed.get('score') or 0.0)
                refined_flag = parsed.get('refined', False)
                # Post-process GPT name: normalize whitespace and common suffixes
                def _normalize_suffix(n: str, source_text: str) -> str:
                    if not n:
                        return n
                    s = n.strip()
                    # collapse repeated phrase sequences
                    s = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", s, flags=re.IGNORECASE)
                    s = re.sub(r'\s{2,}', ' ', s)
                    # normalize common suffix variants
                    if re.search(r'\b(PVT|PVT\.|PRIVATE\s+LIMITED|PRIVATE|LIMITED|LTD|LLP)\b', source_text, re.IGNORECASE):
                        # if gpt removed suffix but source had it, append normalized 'Pvt Ltd' when appropriate
                        if not re.search(r'\b(PVT|PVT\.|PRIVATE\s+LIMITED|LIMITED|LTD|LLP)\b', s, re.IGNORECASE):
                            # prefer 'Pvt Ltd' if 'Pvt' or 'Pvt.' present in source
                            if re.search(r'\bPVT\b|\bPVT\.', source_text, re.IGNORECASE):
                                s = s + ' Pvt Ltd'
                            elif re.search(r'\bPRIVATE\s+LIMITED\b', source_text, re.IGNORECASE):
                                s = s + ' Private Limited'
                            elif re.search(r'\bLTD\b|\bLIMITED\b', source_text, re.IGNORECASE):
                                s = s + ' Ltd'
                    # final strip
                    return s.strip(' ,.-')

                name_norm = _normalize_suffix(name, candidate_text_s or candidate_text) if name else None
                if name_norm:
                    # dedupe obvious repeated phrases
                    def _dedupe_repeated_phrases(s: str) -> str:
                        # Remove immediate repeated multi-word phrases (e.g. "X Y Z X Y Z") -> "X Y Z"
                        words = s.split()
                        n = len(words)
                        # try window sizes from 6 words down to 2
                        for w in range(min(6, n//2), 1, -1):
                            for i in range(0, n - 2*w + 1):
                                first = ' '.join(words[i:i+w]).strip()
                                second = ' '.join(words[i+w:i+2*w]).strip()
                                if first.lower() == second.lower():
                                    # remove the second occurrence
                                    new_words = words[:i+w] + words[i+2*w:]
                                    return ' '.join(new_words)
                        return s

                    name_norm = _dedupe_repeated_phrases(name_norm)
                    name_norm = re.sub(r'\s{2,}', ' ', name_norm).strip(' ,.-')
                    # If normalized name lacks a suffix but a nearby line contains a suffix, attach it
                    if not re.search(r'\b(PVT|PVT\.|PVT\s+LTD|PVT\s+LTD\.|PVT\s+LTD|PRIVATE\s+LIMITED|LTD|LLP)\b', name_norm, re.IGNORECASE):
                        # check a few lines around the candidate index for suffix tokens
                        nearby_range = range(max(0, top_idx-3), min(len(lines), top_idx+4))
                        for j in nearby_range:
                            ln = (lines[j] or '').strip()
                            if re.search(r'\bPVT\b|\bPVT\.|\bPVT\s+LTD|PRIVATE\s+LIMITED|\bLTD\b|\bLLP\b', ln, re.IGNORECASE):
                                # prefer 'Pvt Ltd' for PVT variants
                                if re.search(r'\bPVT\b|\bPVT\.', ln, re.IGNORECASE):
                                    name_norm = name_norm + ' Pvt Ltd'
                                elif re.search(r'PRIVATE\s+LIMITED', ln, re.IGNORECASE):
                                    name_norm = name_norm + ' Private Limited'
                                elif re.search(r'\bLTD\b|\bLIMITED\b', ln, re.IGNORECASE):
                                    name_norm = name_norm + ' Ltd'
                                break
                return {'consignee': name_norm, 'confidence': conf, 'refined': bool(refined_flag)}
            except Exception:
                logger.exception('[CONSIGNEE.SALVAGE] GPT call/parse failed')
                return None

        # Call GPT on the top candidate
        gpt_out = _call_gpt_for_candidate(top_candidate)
        if gpt_out:
            name = gpt_out.get('consignee')
            conf = float(gpt_out.get('confidence', 0.0) or 0.0)
            refined_flag = gpt_out.get('refined', False)
            if name and ((refined_flag is True) or (conf >= accept_conf)):
                # Final safety: if AI name lacks a suffix but nearby text contains a suffix token,
                # append a normalized suffix (common case: 'Pvt Ltd' on following line).
                final_name = name
                if not re.search(r'\b(PVT|PVT\.|PVT\s+LTD|PRIVATE\s+LIMITED|LTD|LLP)\b', final_name, re.IGNORECASE):
                    # scan a small window around the top candidate for suffix-like short lines
                    nearby_range = range(max(0, top_idx-4), min(len(lines), top_idx+5))
                    for j in nearby_range:
                        ln = (lines[j] or '').strip()
                        if re.search(r'\bPVT\b|\bPVT\.|\bPVT\s+LTD|PRIVATE\s+LIMITED|\bLTD\b|\bLLP\b', ln, re.IGNORECASE):
                            if re.search(r'\bPVT\b|\bPVT\.', ln, re.IGNORECASE):
                                final_name = final_name + ' Pvt Ltd'
                            elif re.search(r'PRIVATE\s+LIMITED', ln, re.IGNORECASE):
                                final_name = final_name + ' Private Limited'
                            elif re.search(r'\bLTD\b|\bLIMITED\b', ln, re.IGNORECASE):
                                final_name = final_name + ' Ltd'
                            break

                logger.info(f"[CONSIGNEE.SALVAGE] GPT returned acceptable result: '{final_name}' (conf={conf})")
                # Final cleanup: remove unwanted short-uppercase tokens (codes like 'IPL', 'HSR')
                def _strip_unwanted_acronyms(s: str) -> str:
                    if not s:
                        return s
                    # Keep a small whitelist of valid short tokens often part of company names
                    whitelist = {'LLP', 'LTD', 'PVT', 'PVT.', 'CO', 'INC', 'PLC', 'GST', 'PAN'}
                    parts = s.split()
                    cleaned_parts = []
                    for i, p in enumerate(parts):
                        up = p.upper()
                        if up in whitelist:
                            cleaned_parts.append(p)
                            continue
                        if re.fullmatch(r'[A-Z]{2,4}', p):
                            next_tok = parts[i+1] if i+1 < len(parts) else None
                            prev_tok = parts[i-1] if i-1 >= 0 else None
                            keep_flag = False
                            if next_tok and re.search(r'[a-z]', next_tok):
                                keep_flag = True
                            if prev_tok and re.search(r'[a-z]', prev_tok):
                                keep_flag = True
                            if next_tok and len(next_tok) > 3:
                                keep_flag = True
                            if prev_tok and len(prev_tok) > 3:
                                keep_flag = True
                            if keep_flag:
                                cleaned_parts.append(p)
                                continue
                            else:
                                continue
                        if re.fullmatch(r'(?:[A-Z]{1,4}[/\\-])+(?:[A-Z]{1,4})', p):
                            continue
                        cleaned_parts.append(p)
                    out = ' '.join(cleaned_parts)
                    # extra pass: remove duplicate adjacent words
                    out = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", out, flags=re.IGNORECASE)
                    out = re.sub(r'\s{2,}', ' ', out).strip(' ,.-')

                    def _remove_duplicated_subseq(text: str) -> str:
                        words = text.split()
                        n = len(words)
                        max_w = min(8, n)
                        for w in range(max_w, 2, -1):
                            for i in range(0, n - w + 1):
                                seq = ' '.join(words[i:i+w])
                                rest = ' '.join(words[i+w:])
                                if seq.lower() in rest.lower():
                                    new_words = words[:i] + words[i+w:]
                                    return ' '.join(new_words)
                        return text

                    out = _remove_duplicated_subseq(out)
                    return out

                final_name = _strip_unwanted_acronyms(final_name)
                return final_name
            else:
                logger.info(f"[CONSIGNEE.SALVAGE] GPT returned low confidence/refined flag: conf={conf} refined={refined_flag}")

    # If we still have the old AI refiner available, fall back to it for a last attempt
    if _HAS_AI and _AI_REFINER:
        for _, cand in candidates[:3]:
            try:
                logger.info(f"[CONSIGNEE.SALVAGE] Calling legacy AI refiner on: '{cand[:140]}'")
                ai_out = _AI_REFINER(cand)
                if isinstance(ai_out, dict):
                    name = ai_out.get('consignee') or ai_out.get('name')
                    conf = float(ai_out.get('confidence', 0) or 0)
                    refined_flag = ai_out.get('refined', None)
                    if name and ((refined_flag is True) or (conf >= accept_conf)):
                        logger.info(f"[CONSIGNEE.SALVAGE] Legacy AI returned acceptable result: '{name}' (conf={conf})")
                        return name
                    else:
                        logger.info(f"[CONSIGNEE.SALVAGE] Legacy AI returned low confidence/refined flag: conf={conf} refined={refined_flag}")
            except Exception:
                logger.exception("[CONSIGNEE.SALVAGE] Legacy AI refiner failed")

    return None
