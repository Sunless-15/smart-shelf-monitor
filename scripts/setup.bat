@echo off
setlocal
echo ====================================================
echo Smart Shelf Monitor - Full System Setup
echo ====================================================

REM Setup Python virtualenv
if not exist "%~dp0\..\..\venv\Scripts\python.exe" (
    echo Creating virtual environment at ..\..\venv...
    python -m venv "%~dp0\..\..\venv"
)

REM Install backend dependencies
echo Installing Python backend dependencies...
call "%~dp0\..\..\venv\Scripts\pip.exe" install -r "%~dp0\..\backend\requirements.txt" pytest

REM Install frontend dependencies
echo Installing React frontend dependencies...
cd /d "%~dp0\..\dashboard"
call npm.cmd install

echo.
echo Setup completed successfully!
echo Use run_all.bat to launch both servers.
pause
