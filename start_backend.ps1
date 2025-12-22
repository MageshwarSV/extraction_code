# Activate venv
Write-Host "Activating venv..."
. .\venv\Scripts\Activate.ps1

# Start Flask Data Transformation API in background
Write-Host "Starting Flask API on port 30019..."
Start-Process -FilePath "python" -ArgumentList "-m engine.extractors.data_transformation --api --host 0.0.0.0 --port 30019" -WindowStyle Minimized

# Start FastAPI with Uvicorn in foreground
Write-Host "Starting FastAPI on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
