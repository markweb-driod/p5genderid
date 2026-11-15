# FaceClass Full System Startup Script (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "         FaceClass System Startup (PowerShell)     " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Check Python
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} else {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    Exit 1
}
& $PythonCmd --version
Write-Host "Python OK." -ForegroundColor Green
Write-Host ""

# 2. Check Node.js and npm
Write-Host "[2/5] Checking Node.js and npm..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Red
    Exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] npm is not installed or not in PATH!" -ForegroundColor Red
    Exit 1
}
node -v
Write-Host "Node.js OK." -ForegroundColor Green
Write-Host ""

# 3. Setup Backend Environment
Write-Host "[3/5] Setting up Backend environment..." -ForegroundColor Yellow
$BackendEnv = Join-Path $ScriptDir "backend\.env"
$BackendEnvExample = Join-Path $ScriptDir "backend\.env.example"
if (-not (Test-Path $BackendEnv)) {
    Write-Host "Creating backend\.env from example..." -ForegroundColor Cyan
    Copy-Item $BackendEnvExample $BackendEnv
}

$InstanceDir = Join-Path $ScriptDir "backend\instance"
if (-not (Test-Path $InstanceDir)) {
    New-Item -ItemType Directory -Path $InstanceDir -Force | Out-Null
}

$VenvPython = Join-Path $ScriptDir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python virtual environment in backend\.venv..." -ForegroundColor Cyan
    & $PythonCmd -m venv (Join-Path $ScriptDir "backend\.venv")
    Write-Host "Installing backend dependencies (this may take a couple minutes on first run)..." -ForegroundColor Cyan
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $ScriptDir "backend\requirements.txt")
} else {
    Write-Host "Virtual environment found." -ForegroundColor Green
}

# Ensure database schema is initialized
& $VenvPython -c "import sys; sys.path.insert(0, 'backend'); from app import create_app; create_app()"
Write-Host "Backend environment ready." -ForegroundColor Green
Write-Host ""

# 4. Setup Frontend Dependencies
Write-Host "[4/5] Setting up Frontend dependencies..." -ForegroundColor Yellow
$NodeModules = Join-Path $ScriptDir "node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Host "Installing npm packages (first time setup)..." -ForegroundColor Cyan
    npm install
} else {
    Write-Host "Frontend dependencies already installed." -ForegroundColor Green
}
Write-Host ""

# 5. Launch Servers
Write-Host "[5/5] Launching Servers..." -ForegroundColor Yellow
$BackendDir = Join-Path $ScriptDir "backend"

# Start Backend in a separate window
Start-Process cmd.exe -ArgumentList "/k title FaceClass Backend API (5000) && cd /d `"$BackendDir`" && `"$VenvPython`" run.py"
Write-Host "Backend API started on http://localhost:5000" -ForegroundColor Green

Start-Sleep -Seconds 2

# Start Frontend in a separate window
Start-Process cmd.exe -ArgumentList "/k title FaceClass Frontend (5173) && cd /d `"$ScriptDir`" && npm run dev"
Write-Host "Frontend server started on http://localhost:5173" -ForegroundColor Green

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host " FaceClass is running successfully!               " -ForegroundColor Green
Write-Host " - Frontend:    http://localhost:5173              " -ForegroundColor Cyan
Write-Host " - Backend API: http://localhost:5000/api          " -ForegroundColor Cyan
Write-Host " - Stop script: .\stop_all.ps1 or stop_all.bat    " -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
