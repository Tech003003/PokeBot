@echo off
rem TechBot — launch a Brave instance on a custom CDP port + user-data-dir.
rem
rem Usage (from a cmd prompt):
rem     Start-Brave-Profile.bat 9223 "C:\Users\You\TechBotBrave_B"
rem     Start-Brave-Profile.bat 9224 "C:\Users\You\TechBotBrave_C" "http://user:pass@proxy:8080"
rem
rem Arg 1 : CDP port (must match the CDP URL you enter in the Browsers tab)
rem Arg 2 : user-data-dir (any empty folder you like — one per account)
rem Arg 3 : optional proxy URL (http:// or socks5://) — passed as --proxy-server=...
rem
rem Tip: each account needs its OWN port AND its OWN profile folder.
rem Reusing the same folder on two ports will make Brave complain or crash.

setlocal

set "BRAVE=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
if not exist "%BRAVE%" set "BRAVE=C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"

if not exist "%BRAVE%" (
    echo ERROR: brave.exe not found. Edit this .bat and point BRAVE= to your brave.exe.
    pause & exit /b 1
)

set "PORT=%~1"
if "%PORT%"=="" set "PORT=9222"

set "PROFILE=%~2"
if "%PROFILE%"=="" set "PROFILE=%USERPROFILE%\Desktop\TechBotBraveSession_%PORT%"
if not exist "%PROFILE%" mkdir "%PROFILE%"

set "PROXY_ARG="
if not "%~3"=="" set "PROXY_ARG=--proxy-server=%~3"

title Brave CDP :%PORT%  (%PROFILE%)
echo.
echo Starting Brave
echo   port        : %PORT%
echo   profile dir : %PROFILE%
if not "%PROXY_ARG%"=="" echo   proxy       : %~3
echo.
echo Sign in to your retailer accounts in this window, then go to the TechBot
echo Browsers tab and click CONNECT on the matching row.
echo.
"%BRAVE%" --remote-debugging-port=%PORT% --user-data-dir="%PROFILE%" %PROXY_ARG%
