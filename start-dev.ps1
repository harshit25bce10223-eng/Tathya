<# TATHYA Development Starter Script
This script starts both the backend (FastAPI) and frontend (Vite/React) servers.
Press Ctrl+C to stop both servers.
#>

Write-Host "=== TATHYA Development Server Starter ===" -ForegroundColor Cyan
Write-Host ""

# Function to check if a port is in use
function Test-Port {
    param(
        [int]$Port
    )
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient("127.0.0.1",$Port)
        $tcpClient.Close()
        return $true
    } catch {
        return $false
    }
}

$VENV_PYTHON = "C:\Tathya - AGNITIA\.venv\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) {
    $VENV_PYTHON = "python"
}

Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# 1. Starting Backend
Write-Host "1. Starting Backend (FastAPI on Port 8001)..." -ForegroundColor Cyan

$backendCmd = "cd `\"C:\Tathya - AGNITIA`\" ; & `\"$VENV_PYTHON`\" -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --app-dir backend"
$backendProcess = Start-Process powershell -ArgumentList "-NoExit -Command `"$backendCmd`"" -PassThru

Write-Host "   Waiting for backend to start on port 8001..." -ForegroundColor Gray
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    if (Test-Port -Port 8001) {
        Write-Host "   Backend is running on http://localhost:8001" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
    $waited++
}
if (-not (Test-Port -Port 8001)) {
    Write-Host "   [!] Warning: Backend took longer than expected to respond on 8001." -ForegroundColor Yellow
}

Write-Host ""
# 2. Starting Frontend
Write-Host "2. Starting Frontend (Vite/React)..." -ForegroundColor Cyan

$frontendCmd = "cd `\"C:\Tathya - AGNITIA\frontend`\" ; bun run dev"
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit -Command `"$frontendCmd`"" -PassThru

Write-Host "   Waiting for frontend..." -ForegroundColor Gray
$maxWait = 30
$waited = 0
$fePort = 5173
while ($waited -lt $maxWait) {
    if (Test-Port -Port 5173) {
        $fePort = 5173
        Write-Host "   Frontend is running on http://localhost:5173" -ForegroundColor Green
        break
    } elseif (Test-Port -Port 5174) {
        $fePort = 5174
        Write-Host "   Frontend is running on http://localhost:5174" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
    $waited++
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "TATHYA is now running!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Yellow
Write-Host "  * App / Login:       http://localhost:$fePort/login" -ForegroundColor White
Write-Host "  * Splash Screen:     http://localhost:$fePort/splash" -ForegroundColor White
Write-Host "  * Admin Panel:       http://localhost:$fePort/admin" -ForegroundColor White
Write-Host "  * API Docs:          http://localhost:8001/docs" -ForegroundColor White
Write-Host ""
Write-Host "Demo Credentials (Round 1 Ready):" -ForegroundColor Yellow
Write-Host "  * Reviewer / Demo:   demo@tathya.ai   /  Demo@2024Tathya" -ForegroundColor Green
Write-Host "  * Admin / Superuser: admin@tathya.ai  /  changethis" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C in this window to stop both servers." -ForegroundColor Magenta
Write-Host ""

# Wait loop
$running = $true
while ($running) {
    Start-Sleep -Milliseconds 500
    $backendAlive = (Get-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue) -ne $null
    $frontendAlive = (Get-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue) -ne $null
    if (-not $backendAlive -and -not $frontendAlive) {
        Write-Host "Both servers stopped." -ForegroundColor Green
        break
    }
}