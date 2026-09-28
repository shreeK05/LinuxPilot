#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==========================================="
echo " Starting LinuxPilot...                    "
echo "==========================================="

# Kill old processes holding the ports
echo "-> Freeing ports 8000 and 5173..."
fuser -k 8000/tcp 2>/dev/null || lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "-> Starting Backend API..."
cd apps/api
source .venv/bin/activate
python3 -m uvicorn app.main:app &
BACKEND_PID=$!
cd ../..

echo "-> Starting Frontend UI..."
cd apps/web
npm run dev &
FRONTEND_PID=$!
cd ../..

echo "LinuxPilot is running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
