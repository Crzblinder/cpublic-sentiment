$ErrorActionPreference = "Stop"
Write-Host "Starting CPublic Sentiment locally..."

# Backend venv
if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating backend virtual environment..."
    python -m venv backend\.venv
}
& backend\.venv\Scripts\Activate.ps1
pip install -q -r backend\requirements.txt

# Init DB and seed
cd backend
python scripts\init_db.py
python scripts\seed_data.py
cd ..

# Frontend deps
cd frontend
npm install
cd ..

# Start backend
$backend = Start-Process -FilePath "uvicorn" -ArgumentList "backend.app.main:app --reload --port 8000" -PassThru -NoNewWindow

# Start frontend
$frontend = Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "frontend" -PassThru -NoNewWindow

Write-Host "Backend PID: $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host "Open http://localhost:5173"

Read-Host "Press Enter to stop"
Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
