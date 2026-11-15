@echo off
title FaceClass Docker Startup
echo ===================================================
echo        FaceClass Docker System Startup
echo ===================================================
echo.

cd /d "%~dp0"

where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH!
    echo Please install Docker Desktop from https://www.docker.com/
    pause
    exit /b 1
)

if not exist ".env.production" (
    echo Creating .env.production from .env.production.example...
    copy ".env.production.example" ".env.production" >nul
)

echo Building and starting containers via Docker Compose...
docker compose up --build -d

echo.
echo Containers started!
echo Frontend is available at: http://localhost:8080
echo.
timeout /t 3 /nobreak >nul
start http://localhost:8080
pause
