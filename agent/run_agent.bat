@echo off
title Smart Shelf - Camera Agent
echo ===================================================
echo   Starting Smart Shelf Camera Agent
echo ===================================================

cd /d "%~dp0\.."

if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python agent\camera_agent.py
pause
