@echo off
title NexusBot Command Center
setlocal

cd /d "%~dp0"
cd ..

echo.
echo ==========================================
echo   NexusBot Command Center - First-time setup
echo ==========================================
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python 3.10+ not found.
    echo   Install from https://www.python.org/downloads/ and TICK "Add Python to PATH" on the first screen.
    echo.
    pause & exit /b 1
)

echo [2/5] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Node.js not found.
    echo   Install the LTS build from https://nodejs.org/
    echo.
    pause & exit /b 1
)

if not exist ".venv\" (
    echo [3/5] Creating virtual env...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [3/5] Installing Python deps (this can take a minute)...
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: pip install failed. See messages above.
    pause & exit /b 1
)

echo        Installing Playwright Chromium driver (first run only)...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo WARNING: Playwright driver install reported errors. You may need to re-run Start.bat.
)

if not exist "frontend\build\index.html" (
    echo [4/5] Building frontend (first run only, a few minutes)...
    where yarn >nul 2>&1
    if %errorlevel% neq 0 (
        echo        yarn not found - enabling it via corepack...
        call corepack enable >nul 2>&1
    )
    where yarn >nul 2>&1
    if %errorlevel% neq 0 (
        echo        yarn still not found - installing globally via npm...
        call npm install -g yarn
    )
    pushd frontend
    call yarn install
    if %errorlevel% neq 0 (
        echo        yarn install failed, falling back to npm...
        call npm install
    )
    call yarn build
    if %errorlevel% neq 0 (
        echo        yarn build failed, falling back to npm...
        call npm run build
    )
    popd
) else (
    echo [4/5] Frontend build found, skipping.
)

echo [5/5] Starting dashboard at http://127.0.0.1:8787 ...
echo        (Keep this window open. Close it to stop the bot.)
echo.
python local\launch.py
pause
