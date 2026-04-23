@echo off
title NexusBot Command Center
setlocal

cd /d "%~dp0"
cd ..

echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.10+ not found. Install from https://www.python.org/downloads/ and check "Add to PATH".
    pause & exit /b 1
)

if not exist ".venv\" (
    echo [2/4] Creating virtual env...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] Installing Python deps...
pip install -r backend\requirements.txt --quiet
python -m playwright install chromium

if not exist "frontend\build\index.html" (
    echo [3/4] Building frontend...
    pushd frontend
    call yarn install
    call yarn build
    popd
) else (
    echo [3/4] Frontend build found.
)

echo [4/4] Starting dashboard at http://127.0.0.1:8787 ...
python local\launch.py
pause
