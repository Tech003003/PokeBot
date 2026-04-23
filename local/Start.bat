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
python --version >nul 2>&1 || goto no_python

echo [2/5] Checking Node.js...
node --version >nul 2>&1 || goto no_node

if not exist ".venv\" (
    echo        Creating virtual env...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [3/5] Installing Python deps (this can take a minute)...
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt || goto pip_fail

echo        Installing Playwright Chromium driver (first run only)...
python -m playwright install chromium

if exist "frontend\build\index.html" goto skip_frontend

echo [4/5] Building frontend (first run only, takes a few minutes)...
where yarn >nul 2>&1 || call corepack enable >nul 2>&1
where yarn >nul 2>&1 || call npm install -g yarn
pushd frontend
call yarn install || call npm install
call yarn build || call npm run build
popd
goto run

:skip_frontend
echo [4/5] Frontend build found, skipping.

:run
echo.
echo [5/5] Starting dashboard at http://127.0.0.1:8787 ...
echo        Keep this window open. Close it to stop the bot.
echo.
python local\launch.py
pause
exit /b 0

:no_python
echo.
echo ERROR: Python 3.10+ not found.
echo    Install from https://www.python.org/downloads/ and TICK "Add python.exe to PATH" on the first screen.
pause
exit /b 1

:no_node
echo.
echo ERROR: Node.js not found.
echo    Install the LTS build from https://nodejs.org/ , then re-run this script.
pause
exit /b 1

:pip_fail
echo.
echo ERROR: pip install failed. See messages above.
echo    Common fix: delete the .venv folder and run Start.bat again.
pause
exit /b 1
