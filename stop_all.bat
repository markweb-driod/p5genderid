@echo off
title FaceClass System Shutdown
echo ===================================================
echo           FaceClass System Shutdown
echo ===================================================
echo.
echo Stopping services on Port 5000 (Backend API) and Port 5173 (Frontend)...

set FOUND=0

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo Stopping Backend process (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
    set FOUND=1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo Stopping Frontend process (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
    set FOUND=1
)

if %FOUND% equ 0 (
    echo No active FaceClass services found running on ports 5000 or 5173.
) else (
    echo All FaceClass services have been stopped.
)

echo.
pause
