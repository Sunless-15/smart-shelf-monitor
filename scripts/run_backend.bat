@echo off
setlocal
echo ====================================================
echo Starting Smart Shelf Monitor Backend...
echo ====================================================

cd /d "%~dp0\..\backend"

REM Find python in workspace venv or system
if exist "%~dp0\..\..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0\..\..\venv\Scripts\python.exe"
) else if exist "%~dp0\..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0\..\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" app.py

pause
