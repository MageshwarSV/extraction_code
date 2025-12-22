#Dockerfile image name wbai-ocr
# Use slim Python base
FROM python:3.10-slim

# Install system dependencies (OCR tools + build tools)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libtesseract-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Tesseract data location (for pytesseract)
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Expose FastAPI port and Flask API port
EXPOSE 8000
EXPOSE 30019

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run both FastAPI and Flask API
CMD ["/app/start.sh"]
