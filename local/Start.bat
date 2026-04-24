@echo off
title TechBot Command Center
setlocal

cd /d "%~dp0"
cd ..

echo.
echo ==========================================
echo   TechBot Command Center - starting up
echo ==========================================
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1 || goto no_python

echo [2/5] Checking Node.js...
node --version >nul 2>&1 || goto no_node

if not exist ".venv\" python -m venv .venv
call .venv\Scripts\activate.bat

echo [3/5] Installing/updating Python deps...
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt || goto pip_fail

if not exist "ms-playwright\" (
    echo        Installing Playwright Chromium driver (first run only)...
    python -m playwright install chromium
)

rem ----- Decide whether to rebuild the frontend -----
if not exist "frontend\build\index.html" goto do_build
powershell -NoProfile -ExecutionPolicy Bypass -File "local\check_rebuild.ps1"
if errorlevel 1 goto do_build
echo [4/5] Frontend build up to date, skipping rebuild.
goto run

:do_build
echo [4/5] Building frontend (first run or source changed, takes a few minutes)...
where yarn >nul 2>&1 || call corepack enable >nul 2>&1
where yarn >nul 2>&1 || call npm install -g yarn
pushd frontend
call yarn install || call npm install
call yarn build || call npm run build
popd

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
echo ERROR: Python 3.10+ not found. Install from https://www.python.org/downloads/ and TICK "Add python.exe to PATH".
pause
exit /b 1

:no_node
echo.
echo ERROR: Node.js not found. Install the LTS build from https://nodejs.org/.
pause
exit /b 1

:pip_fail
echo.
echo ERROR: pip install failed. See messages above. Common fix: delete the .venv folder and re-run.
pause
exit /b 1
