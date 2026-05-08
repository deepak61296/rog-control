#!/bin/bash
# Launch ROG Control desktop app

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting ROG Control..."

# Kill old processes
echo "Cleaning old processes..."
pkill -f "python3.*server.py" 2>/dev/null || true
pkill -f "electron" 2>/dev/null || true
sleep 1

# Start Python WebSocket server
echo "Starting Python server..."
nohup python3 "$PROJECT_ROOT/src/server.py" > /tmp/rog-server.log 2>&1 &
sleep 2

# Check if server is running
if ! ss -tlnp 2>/dev/null | grep -q 9876; then
    echo "ERROR: Python server failed to start. Check /tmp/rog-server.log"
    cat /tmp/rog-server.log
    exit 1
fi
echo "Python server OK (ws://127.0.0.1:9876)"

# Start Electron
echo "Starting Electron app..."
cd "$SCRIPT_DIR"
DISPLAY=:1 ./node_modules/.bin/electron . > /tmp/rog-electron.log 2>&1 &
sleep 3

# Check if Electron is running
if ps aux | grep -v grep | grep -q electron; then
    echo "Electron app launched successfully!"
    echo "If you don't see a window, check /tmp/rog-electron.log"
    echo ""
    echo "To view logs:"
    echo "  Python server: tail -f /tmp/rog-server.log"
    echo "  Electron app:   tail -f /tmp/rog-electron.log"
else
    echo "ERROR: Electron failed to start. Check /tmp/rog-electron.log"
    cat /tmp/rog-electron.log
    exit 1
fi
