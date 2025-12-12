#!/bin/bash

# Stop Script
# Kills processes on ports 8000 and 3000

set -e

echo "=== Stopping Servers ==="

# Kill backend (port 8000)
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "Stopping backend server (port 8000)..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    echo "Backend stopped."
else
    echo "No process found on port 8000."
fi

# Kill frontend (port 3000)
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "Stopping frontend server (port 3000)..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    echo "Frontend stopped."
else
    echo "No process found on port 3000."
fi

echo "=== All servers stopped ==="

