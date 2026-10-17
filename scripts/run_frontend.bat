@echo off
setlocal
echo ====================================================
echo Starting Smart Shelf Monitor Frontend (Vite)...
echo ====================================================

if exist "%~dp0\..\dashboard" (
    cd /d "%~dp0\..\dashboard"
) else if exist "%~dp0\..\smart shelf\dashboard" (
    cd /d "%~dp0\..\smart shelf\dashboard"
)

echo Running: npm.cmd run dev -- --host
call npm.cmd run dev -- --host

pause
