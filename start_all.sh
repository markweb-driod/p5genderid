#!/usr/bin/env bash
# FaceClass Full System Startup Script (Linux / macOS / WSL)
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "==================================================="
echo "         FaceClass System Startup (Shell)         "
echo "==================================================="
echo ""

# 1. Check Python
echo "[1/5] Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3 is not installed or not in PATH!"
    exit 1
fi
$PYTHON_CMD --version
echo "Python OK."
echo ""

# 2. Check Node.js and npm
echo "[2/5] Checking Node.js and npm..."
if ! command -v node >/dev/null 2>&1; then
    echo "[ERROR] Node.js is not installed!"
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] npm is not installed!"
    exit 1
fi
node -v
echo "Node.js OK."
echo ""

# 3. Setup Backend Environment
echo "[3/5] Setting up Backend environment..."
if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env from example..."
    cp "backend/.env.example" "backend/.env"
fi

mkdir -p "backend/instance"

if [ ! -f "backend/.venv/bin/python" ]; then
    echo "Creating virtual environment in backend/.venv..."
    $PYTHON_CMD -m venv backend/.venv
    echo "Installing backend dependencies..."
    backend/.venv/bin/pip install --upgrade pip
    backend/.venv/bin/pip install -r backend/requirements.txt
else
    echo "Virtual environment found."
fi

# Initialize database schema
backend/.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from app import create_app; create_app()"
echo "Backend environment ready."
echo ""

# 4. Setup Frontend Dependencies
echo "[4/5] Setting up Frontend dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing npm packages (first time setup)..."
    npm install
else
    echo "Frontend dependencies already installed."
fi
echo ""

# 5. Launch Servers
echo "[5/5] Launching Servers..."

# Start Backend API
(cd backend && .venv/bin/python run.py) > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend.pid
echo "Backend API running in background (PID $BACKEND_PID) on http://localhost:5000"

sleep 2

# Start Frontend
npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > .frontend.pid
echo "Frontend running in background (PID $FRONTEND_PID) on http://localhost:5173"

echo ""
echo "==================================================="
echo " FaceClass is running successfully!"
echo " - Frontend:    http://localhost:5173"
echo " - Backend API: http://localhost:5000/api"
echo " - Stop script: ./stop_all.sh"
echo "==================================================="
echo ""

# Try opening default browser
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:5173" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "http://localhost:5173" >/dev/null 2>&1 &
fi
