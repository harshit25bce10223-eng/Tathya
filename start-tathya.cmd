@echo off
title TATHYA - Server Starter
color 0A

echo.
echo ============================================
echo  TATHYA Development Server Starter
echo ============================================
echo.

set "BACKEND_DIR=C:\Tathya - AGNITIA\backend"
set "FRONTEND_DIR=C:\Tathya - AGNITIA\frontend"
set "VENV_PY=C:\Tathya - AGNITIA\.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    set "VENV_PY=python"
)

echo [1/2] Starting Backend Server (FastAPI on port 8001)...
start "Tathya Backend" cmd /k "cd /d C:\Tathya - AGNITIA && "%VENV_PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --app-dir backend"

timeout /t 3 >nul

echo [2/2] Starting Frontend Server (Vite/React via Bun)...
start "Tathya Frontend" cmd /k "cd /d %FRONTEND_DIR% && bun run dev"

timeout /t 3 >nul

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo  Access Points:
echo   * Login Page:     http://localhost:5173/login (or 5174)
echo   * Splash Screen:  http://localhost:5173/splash
echo   * Admin Panel:    http://localhost:5173/admin
echo   * API Docs:       http://localhost:8001/docs
echo.
echo  Demo Credentials (Round 1 Ready):
echo   * Reviewer/Demo:  demo@tathya.ai  /  Demo@2024Tathya
echo   * Superuser:      admin@tathya.ai /  changethis
echo.
echo  Opening browser to Tathya...
start "" "http://localhost:5173/login"

pause