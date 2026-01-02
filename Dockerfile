# ================================================================
# Dockerfile for WBAI Document Extractor Engine
# ================================================================
# Created based on comprehensive analysis of all project files:
# - FastAPI app in app/main.py (port 8000)
# - Flask API in engine/ for data transformation (port 30019)
# - Core extractors using: Tesseract, Poppler, EasyOCR, PaddleOCR
# - Python deps: pytesseract, pdf2image, opencv, PIL, numpy, etc.
# ================================================================

FROM python:3.12-slim

# ================================================================
# SYSTEM DEPENDENCIES
# ================================================================
# Based on analysis of engine/core.py, engine/extractors/*.py:
#   - Tesseract OCR (pytesseract requires tesseract-ocr binary)
#   - Poppler (pdf2image requires poppler-utils for pdftoppm)
#   - OpenCV deps (libgl1, libglib2.0-0, libsm6, libxext6, libxrender1)
#   - Build tools for pip packages with native extensions
# ================================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR (used by pytesseract in all extractors)
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    # Poppler utils (used by pdf2image in core.py, client1_format1.py)
    poppler-utils \
    # OpenCV dependencies (cv2 used in delivery_address.py, deskew.py)
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Build tools for native pip packages
    gcc \
    g++ \
    libgomp1 \
    # Wget for downloading tessdata
    wget \
    && rm -rf /var/lib/apt/lists/*

# ================================================================
# TESSDATA - Download English trained data (matches local)
# ================================================================
# Analysis: pytesseract uses TESSDATA_PREFIX environment variable
# Default Debian tessdata is old (2019), download latest from GitHub
# ================================================================

ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
RUN wget -q -O ${TESSDATA_PREFIX}/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

# ================================================================
# WORK DIRECTORY
# ================================================================

WORKDIR /app

# ================================================================
# PYTHON DEPENDENCIES
# ================================================================
# Based on requirements.txt analysis + import scanning of all .py files:
#
# From requirements.txt:
#   - flask-cors, PyPDF2, rich, loguru, PyMuPDF, easyocr
#   - paddlepaddle, paddleocr
#
# From import analysis (engine/extractors/*.py, app/main.py):
#   - pytesseract (all extractors)
#   - pdf2image (core.py, client1_format1.py, delivery_address.py)
#   - opencv-python (cv2 in delivery_address.py, deskew.py, perspective_correction.py)
#   - numpy (all extractors)
#   - Pillow (PIL in all image processing)
#   - fastapi, uvicorn (app/main.py)
#   - python-dotenv (app/main.py)
#   - psycopg2-binary (app/main.py - optional DB)
# ================================================================

# Copy requirements first for Docker layer caching
COPY requirements.txt /app/

# Install CPU-only PyTorch first (required by easyocr, paddleocr)
# This prevents ~2GB download of GPU version
RUN pip install --no-cache-dir --default-timeout=600 \
    torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cpu

# Install all dependencies from requirements.txt
RUN pip install --no-cache-dir --default-timeout=600 -r requirements.txt

# Install additional dependencies found in import analysis
RUN pip install --no-cache-dir --default-timeout=600 \
    pytesseract \
    pdf2image \
    opencv-python-headless \
    pillow \
    fastapi \
    uvicorn \
    python-dotenv \
    psycopg2-binary \
    python-multipart

# ================================================================
# COPY APPLICATION CODE
# ================================================================

COPY . /app

# ================================================================
# ENVIRONMENT VARIABLES
# ================================================================
# Based on analysis of engine/core.py, app/main.py:
#   - TESSDATA_PREFIX: Path to tessdata (already set above)
#   - No POPPLER_PATH needed on Linux (uses system poppler-utils)
# 
# Performance/compatibility fixes from previous debugging:
#   - Disable oneDNN to prevent CPU compatibility issues
#   - Limit thread count for predictable behavior
# ================================================================

ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Disable oneDNN/MKL (fixes "could not create primitive" on some servers)
ENV ONEDNN_PRIMITIVE_CACHE_CAPACITY=0
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV DNNL_VERBOSE=0
ENV MKLDNN_VERBOSE=0
ENV PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

# ================================================================
# PORTS
# ================================================================
# Based on start.sh and app/main.py:
#   - FastAPI runs on port 8000 (main extraction API)
#   - Flask runs on port 30019 (data transformation API)
# ================================================================

EXPOSE 8000
EXPOSE 30019

# ================================================================
# STARTUP
# ================================================================
# start.sh runs both APIs:
#   1. Flask data transformation API (background, port 30019)
#   2. FastAPI extraction API (foreground, port 8000)
# ================================================================

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
