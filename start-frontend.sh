#!/bin/bash

# Frontend Startup Script
# Kills any process on port 3000 and starts the Next.js frontend server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"

echo "=== Starting Frontend Server ==="

# Kill any process using port 3000
echo "Checking for processes on port 3000..."
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "Killing existing process on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Check if node_modules exists
cd "${FRONTEND_DIR}"
if [ ! -d "node_modules" ]; then
    echo "node_modules not found. Installing dependencies..."
    npm install
fi

echo "Starting Next.js development server on port 3000..."
npm run dev

