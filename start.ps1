# Start Backend and Frontend for AstroSense

# This PowerShell script starts both the FastAPI backend and React frontend
# Run from the project root directory

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Starting AstroSense Development" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if we can start the backend
Write-Host "Setting up Backend..." -ForegroundColor Green
$serverPath = ".\server"
if (-not (Test-Path $serverPath)) {
    Write-Host "Error: server directory not found" -ForegroundColor Red
    exit 1
}

# Check if we can start the frontend
Write-Host "Setting up Frontend..." -ForegroundColor Green
$clientPath = ".\client"
if (-not (Test-Path $clientPath)) {
    Write-Host "Error: client directory not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Starting Backend (Port 8000)..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Start backend in background
$backend = Start-Process -FilePath "powershell" -ArgumentList @"
cd server
`$venvPath = 'venv\Scripts\Activate.ps1'
if (Test-Path `$venvPath) {
    & `$venvPath
} else {
    Write-Host 'Virtual env not found. Creating...'
    python -m venv venv
    & 'venv\Scripts\Activate.ps1'
    pip install -r requirements.txt
}
Write-Host 'Starting FastAPI server...'
python -m uvicorn app.main:app --reload
"@ -PassThru

Write-Host ""
Write-Host "Wait a moment for backend to start..."
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Starting Frontend (Port 5173)..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Start frontend in background
$frontend = Start-Process -FilePath "powershell" -ArgumentList @"
cd client
npm install
npm run dev
"@ -PassThru

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Both servers are starting!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Yellow
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop servers" -ForegroundColor Yellow
Write-Host ""

# Keep this window open
Read-Host "Press Enter to close this window (servers will continue running)"
