@echo off
title Brave with CDP :9222
setlocal

set "BRAVE=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
if not exist "%BRAVE%" set "BRAVE=C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"

if not exist "%BRAVE%" (
    echo ERROR: brave.exe not found at default paths. Edit this .bat and point BRAVE= to your brave.exe
    pause & exit /b 1
)

set "PROFILE=%USERPROFILE%\Desktop\NexusBotBraveSession"
if not exist "%PROFILE%" mkdir "%PROFILE%"

echo Starting Brave with --remote-debugging-port=9222
echo Log into your retailer accounts in this window, then return to the dashboard and click CONNECT BRAVE.
"%BRAVE%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%"
