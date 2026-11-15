@echo off
setlocal enabledelayedexpansion
title FaceClass System Startup

echo ===================================================
echo           FaceClass System Startup
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
echo [1/5] Checking Python installation...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where py >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python 3.10+ from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)
%PYTHON_CMD% --version
echo Python OK.
echo.

:: 2. Check Node.js and npm
echo [2/5] Checking Node.js and npm...
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not found! Please check your Node.js installation.
    pause
    exit /b 1
)
node -v
echo Node.js OK.
echo.

:: 3. Prepare Backend Environment
echo [3/5] Setting up Backend environment...
if not exist "backend\.env" (
    echo Copying backend\.env.example to backend\.env...
    copy "backend\.env.example" "backend\.env" >nul
)

if not exist "backend\instance" (
    mkdir "backend\instance" >nul 2>nul
)

if not exist "backend\.venv\Scripts\python.exe" (
    echo Creating Python virtual environment in backend\.venv...
    %PYTHON_CMD% -m venv backend\.venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Installing backend dependencies (this may take a couple minutes on first run)...
    backend\.venv\Scripts\python.exe -m pip install --upgrade pip
    backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [WARNING] Some dependencies failed to install. Continuing...
    )
) else (
    echo Virtual environment found at backend\.venv.
)

:: Verify database initialization
backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from app import create_app; create_app()" >nul 2>nul
echo Backend setup complete.
echo.

:: 4. Prepare Frontend Dependencies
echo [4/5] Setting up Frontend dependencies...
if not exist "node_modules" (
    echo Running npm install (first time setup)...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] npm install failed!
        pause
        exit /b 1
    )
) else (
    echo Frontend dependencies already installed.
)
echo Frontend setup complete.
echo.

:: 5. Launch Backend and Frontend
echo [5/5] Launching Servers...
echo Starting Backend API server on http://localhost:5000 ...
start "FaceClass API (Port 5000)" cmd /k "cd /d ""%~dp0backend"" && ""%~dp0backend\.venv\Scripts\python.exe"" run.py"

timeout /t 2 /nobreak >nul

echo Starting Frontend Dev Server on http://localhost:5173 ...
start "FaceClass Frontend (Port 5173)" cmd /k "cd /d ""%~dp0"" && npm run dev"

echo.
echo ===================================================
echo  FaceClass is now starting up!
echo.
echo  - Frontend: http://localhost:5173
echo  - Backend API: http://localhost:5000/api
echo.
echo  Opening browser...
echo  To shut down both servers, run stop_all.bat
echo ===================================================

timeout /t 3 /nobreak >nul
start http://localhost:5173

pause
