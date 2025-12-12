#!/bin/bash

# Backend Startup Script
# Kills any process on port 8000 and starts the FastAPI backend server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
VENV_PATH="${BACKEND_DIR}/.venv"

echo "=== Starting Backend Server ==="

# Kill any process using port 8000
echo "Checking for processes on port 8000..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "Killing existing process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Verify virtual environment exists
if [ ! -d "${VENV_PATH}" ]; then
    echo "ERROR: Virtual environment not found at ${VENV_PATH}"
    echo "Please create it first: cd backend && python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment and start server
echo "Activating virtual environment..."
cd "${BACKEND_DIR}"
source "${VENV_PATH}/bin/activate"

echo "Starting uvicorn server on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000

