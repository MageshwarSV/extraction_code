#!/bin/bash

# Start Flask Data Transformation API in background
echo "Starting Flask API on port 30019..."
python -m engine.extractors.data_transformation --api --host 0.0.0.0 --port 30019 &

# Start FastAPI with Uvicorn in foreground
echo "Starting FastAPI on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
