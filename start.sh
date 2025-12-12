#!/bin/bash

# Combined Startup Script
# Kills existing processes, starts backend, waits for health check, then starts frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
VENV_PATH="${BACKEND_DIR}/.venv"
LOG_DIR="${SCRIPT_DIR}/logs"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

# Create logs directory
mkdir -p "${LOG_DIR}"

echo "=== Starting Compensation Assistant ==="

# Kill existing processes
echo "Stopping existing servers..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "  Killing process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

if lsof -ti:3000 > /dev/null 2>&1; then
    echo "  Killing process on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

sleep 2

# Verify virtual environment exists
if [ ! -d "${VENV_PATH}" ]; then
    echo "ERROR: Virtual environment not found at ${VENV_PATH}"
    echo "Please create it first: cd backend && python3 -m venv .venv"
    exit 1
fi

# Start backend
echo ""
echo "=== Starting Backend Server ==="
cd "${BACKEND_DIR}"
source "${VENV_PATH}/bin/activate"

# Start backend in background
echo "Starting backend server on port 8000..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: ${BACKEND_PID}"

# Wait for backend to be healthy
echo "Waiting for backend to be ready..."
MAX_WAIT=30
WAIT_COUNT=0
while [ ${WAIT_COUNT} -lt ${MAX_WAIT} ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is healthy!"
        break
    fi
    echo "  Waiting... (${WAIT_COUNT}/${MAX_WAIT})"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ ${WAIT_COUNT} -ge ${MAX_WAIT} ]; then
    echo "ERROR: Backend failed to start within ${MAX_WAIT} seconds"
    echo "Check logs at: ${BACKEND_LOG}"
    kill ${BACKEND_PID} 2>/dev/null || true
    exit 1
fi

# Start frontend
echo ""
echo "=== Starting Frontend Server ==="
cd "${FRONTEND_DIR}"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
echo "Starting frontend server on port 3000..."
nohup npm run dev > "${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: ${FRONTEND_PID}"

# Wait for frontend to be ready
echo "Waiting for frontend to be ready..."
MAX_WAIT=30
WAIT_COUNT=0
while [ ${WAIT_COUNT} -lt ${MAX_WAIT} ]; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "Frontend is ready!"
        break
    fi
    echo "  Waiting... (${WAIT_COUNT}/${MAX_WAIT})"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ ${WAIT_COUNT} -ge ${MAX_WAIT} ]; then
    echo "WARNING: Frontend may not be ready yet. Check logs at: ${FRONTEND_LOG}"
fi

echo ""
echo "=== Servers Started Successfully ==="
echo "Backend:  http://localhost:8000 (PID: ${BACKEND_PID})"
echo "Frontend: http://localhost:3000 (PID: ${FRONTEND_PID})"
echo ""
echo "Logs:"
echo "  Backend:  ${BACKEND_LOG}"
echo "  Frontend: ${FRONTEND_LOG}"
echo ""
echo "To stop servers, run: ./stop.sh"
echo ""
