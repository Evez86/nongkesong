@echo off
rem ============================================================
rem  Pine Letters API - one-click start (Windows cmd)
rem  Usage:  start_api.bat            -> http://127.0.0.1:8000
rem          start_api.bat 8010       -> http://127.0.0.1:8010
rem  Stop with Ctrl+C, or just close this window.
rem ============================================================
setlocal
cd /d "%~dp0"

set "PORT=8000"
if not "%~1"=="" set "PORT=%~1"

set "PY="
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto run
where py >nul 2>nul
if errorlevel 1 goto nopy
set "PY=py -3"

:run
echo.
echo   Pine Letters API
echo   http://127.0.0.1:%PORT%/
echo   Press Ctrl+C to stop
echo.
cmd /c %PY% api\devserver.py --port %PORT%
echo.
echo Server stopped.
pause
exit /b 0

:nopy
echo.
echo [ERROR] Python not found in PATH. Install Python 3.10+ first.
pause
exit /b 1
