# AI Refinement Setup Guide

## Overview

The system now uses **TWO AI services**:

1. **Google Gemini** - For delivery address formatting (`delivery_address.py` → `ai.py`)
2. **OpenAI ChatGPT** - For validating and correcting ALL other fields (`ai_refine_all_fields.py`)

This dual approach ensures:
- ✅ Delivery addresses are properly formatted and cleaned (Gemini)
- ✅ All other fields (Vehicle, L.R., E-Way, etc.) are validated and corrected (ChatGPT)
- ✅ OCR errors are intelligently fixed (e.g., TN11BK7553 → TN18K7553)
- ✅ Missing fields are filled when possible from context

---

## Setup Instructions

### 1. Install OpenAI SDK

```bash
pip install openai
```

### 2. Get OpenAI API Key

1. Go to: https://platform.openai.com/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

### 3. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-your-api-key-here"
```

**Windows (Permanent - System Environment Variables):**
1. Search "Environment Variables" in Windows
2. Click "New" under User Variables
3. Variable name: `OPENAI_API_KEY`
4. Variable value: `sk-your-api-key-here`

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

Add to `~/.bashrc` or `~/.zshrc` for persistence:
```bash
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Verify Setup

Test the AI refinement:

```bash
cd c:\Users\avin4\Desktop\wbai_doc_extractor_engine-maincopy
python -m engine.extractors.ai_refine_all_fields
```

You should see:
```
Testing AI refinement...
============================================================
[INFO] [AI Refine] Attempt 1/3...
[INFO] [AI Refine] ✓ Fields corrected:
  • Vehicle: 'TN11BK7553' → 'TN18K7553'
    Reason: OCR error - "11B" should be "18" (district code)
...
```

---

## Configuration

### Environment Variables

All AI refinement settings can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use (gpt-4o-mini is cost-effective) |
| `OPENAI_MAX_RETRIES` | `3` | Max retry attempts if API fails |
| `OPENAI_WAIT_SECONDS` | `2` | Initial wait time between retries |
| `OPENAI_BACKOFF_MULTIPLIER` | `2.0` | Backoff multiplier (2.0 = double wait each retry) |
| `OPENAI_TEMPERATURE` | `0.1` | Creativity (0.1 = very consistent/deterministic) |

**Example custom configuration:**

```powershell
# Use GPT-4o for higher accuracy (more expensive)
$env:OPENAI_MODEL = "gpt-4o"

# More retries for unreliable networks
$env:OPENAI_MAX_RETRIES = "5"

# Longer wait for rate-limited accounts
$env:OPENAI_WAIT_SECONDS = "5"
```

---

## Cost Optimization

### Recommended Settings

For **production** with cost control:
```powershell
$env:OPENAI_MODEL = "gpt-4o-mini"      # Cheapest, fast, good quality
$env:OPENAI_MAX_RETRIES = "2"          # Reduce retries
$env:OPENAI_TEMPERATURE = "0.1"        # Consistent output
```

For **maximum accuracy** (higher cost):
```powershell
$env:OPENAI_MODEL = "gpt-4o"           # Best quality
$env:OPENAI_MAX_RETRIES = "3"
$env:OPENAI_TEMPERATURE = "0.0"        # Fully deterministic
```

### Estimated Costs (as of 2024)

**gpt-4o-mini** (recommended):
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens
- ~$0.002 per invoice (very cheap!)

**gpt-4o** (high accuracy):
- Input: $2.50 / 1M tokens  
- Output: $10.00 / 1M tokens
- ~$0.03 per invoice

---

## How It Works

### Extraction Flow

```
1. PDF → Tesseract OCR
   ↓
2. Extract all fields (Invoice, L.R., Vehicle, E-Way, etc.)
   ↓
3. Delivery Address → PaddleOCR → Gemini AI formatting
   ↓
4. ALL OTHER FIELDS → ChatGPT validation & correction ← NEW!
   ↓
5. Database transformation (consignee/destination mapping)
   ↓
6. Return final data
```

### What ChatGPT Fixes

**Vehicle Numbers:**
- `TN11BK7553` → `TN18K7553` (OCR error: "11B" = "18")
- `KA1BAN0922` → `KA18AN0922` (OCR error: "1B" = "18")
- `TN458Q0372` → `TN45BQ0372` (OCR error: "8" = "B" in series)

**E-Way Bill Numbers:**
- Removes datetime patterns (510202523590)
- Validates exactly 12 digits
- Fixes OCR digit errors (O→0, I→1, S→5)

**Mobile Numbers:**
- Validates 10 digits starting with 6/7/8/9
- Fixes OCR errors in digits
- Ensures proper Indian mobile format

**L.R./Consignment Numbers:**
- Filters out HSN codes (2523, 6996)
- Filters out dates (03102025)
- Validates 2-7 digit format

**Dates:**
- Normalizes to DD.MM.YYYY format
- Fixes OCR errors (O→0, I→1 in dates)

**Missing Fields:**
- Attempts to fill from OCR context
- Uses invoice intelligence to infer missing data

---

## Troubleshooting

### "OpenAI SDK not installed"

```bash
pip install openai
```

### "OPENAI_API_KEY not found"

Set the environment variable (see Setup section above).

### "AI refinement failed: Rate limit"

You're hitting OpenAI rate limits. Solutions:
1. Increase `OPENAI_WAIT_SECONDS` to 5-10
2. Reduce `OPENAI_MAX_RETRIES` to 1-2
3. Upgrade your OpenAI plan for higher limits

### "Max retries reached"

Network or API issues. Check:
1. Internet connection
2. OpenAI API status: https://status.openai.com/
3. API key is valid and has credits
4. Increase `OPENAI_MAX_RETRIES` if needed

### "Fields not being corrected"

ChatGPT might think the data is correct. Enable debug logging:

```python
import logging
logging.getLogger("engine.extractors.ai_refine_all_fields").setLevel(logging.DEBUG)
```

Check the AI's reasoning in the logs.

---

## Testing

### Test AI Refinement Only

```bash
python -m engine.extractors.ai_refine_all_fields
```

### Test Full Extraction with AI

```bash
python engine/extractors/client1_format1.py "uploads/your-invoice.pdf"
```

Look for these log sections:
```
============================================================
AI REFINEMENT: ChatGPT validation & correction...
============================================================
[INFO] [AI Refine] Attempt 1/3...
[INFO] [AI Refine] ✓ Fields corrected:
  • Vehicle: 'TN11BK7553' → 'TN18K7553'
    Reason: OCR error - "11B" should be "18" (district code)
...
```

---

## Disabling AI Refinement

If you want to skip AI refinement (faster, no API costs):

**Method 1: Don't install OpenAI SDK**
```bash
pip uninstall openai
```

**Method 2: Don't set API key**
```powershell
Remove-Item Env:OPENAI_API_KEY
```

The system will gracefully fall back to non-AI extraction.

---

## Support

For issues or questions:
1. Check logs for error messages
2. Verify API key and credits
3. Test with sample invoices
4. Check OpenAI API status

**API Key Issues:** https://platform.openai.com/api-keys
**Billing/Credits:** https://platform.openai.com/usage
**API Status:** https://status.openai.com/
