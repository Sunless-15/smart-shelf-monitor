@echo off
setlocal
echo ====================================================
echo Launching Smart Shelf Monitor Full-Stack App
echo ====================================================

echo Starting Backend Server in new window...
start "Smart Shelf Backend" cmd /k "call "%~dp0\run_backend.bat""

timeout /t 3 /nobreak > nul

echo Starting Frontend Dev Server in new window...
start "Smart Shelf Frontend" cmd /k "call "%~dp0\run_frontend.bat""

echo.
echo ====================================================
echo Backend running on:  http://localhost:5000
echo Frontend running on: http://localhost:5173
echo ====================================================
echo.
