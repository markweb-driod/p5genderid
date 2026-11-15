#!/usr/bin/env bash
# FaceClass Shutdown Script (Linux / macOS / WSL)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "Stopping FaceClass services..."

if [ -f .backend.pid ]; then
    PID=$(cat .backend.pid)
    kill $PID 2>/dev/null || true
    rm -f .backend.pid
    echo "Stopped backend (PID $PID)"
fi

if [ -f .frontend.pid ]; then
    PID=$(cat .frontend.pid)
    kill $PID 2>/dev/null || true
    rm -f .frontend.pid
    echo "Stopped frontend (PID $PID)"
fi

# Fallback check for ports 5000 and 5173
for PORT in 5000 5173; do
    PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        echo "Killed remaining process on port $PORT (PID $PID)"
    fi
done

echo "FaceClass stopped."
