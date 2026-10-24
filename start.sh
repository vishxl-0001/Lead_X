#!/usr/bin/env bash

# ==============================================================================
# LeadFinder - B2B Google Maps & WhatsApp Lead Extractor Launcher
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo "🚀 Starting LeadFinder Platform..."
echo "=================================================="

# Check Python dependencies
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing/verifying Python requirements..."
pip install -r requirements.txt -q

# Install playwright browsers if not installed
echo "Checking Playwright Chromium browser..."
"$DIR/venv/bin/python3" -m playwright install chromium || true

# Check Frontend dependencies
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "=================================================="
echo "Starting Backend (FastAPI on http://localhost:8000)..."
cd "$DIR"
"$DIR/venv/bin/python3" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Starting Frontend (Vite on http://localhost:3000)..."
cd "$DIR/frontend"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; exit" SIGINT SIGTERM

echo "=================================================="
echo "🎉 LeadFinder is running!"
echo "👉 Web Dashboard: http://localhost:3000"
echo "👉 API & Swagger Docs: http://localhost:8000/docs"
echo "=================================================="
echo "Press Ctrl+C to stop both servers."

wait
