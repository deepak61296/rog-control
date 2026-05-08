#!/bin/bash
# ROG Control - Full app launcher
# Run this: bash /home/deepak/Documents/Projects/rog-control/desktop/start.sh

set -e
cd /home/deepak/Documents/Projects/rog-control

echo "=== Killing old processes ==="
pkill -9 -f "src/server.py" 2>/dev/null || true
pkill -9 -f "electron" 2>/dev/null || true
sleep 2

echo "=== Checking port 9876 ==="
if ss -tlnp 2>/dev/null | grep -q 9876; then
    echo "ERROR: Port 9876 still in use! Trying harder..."
    PID=$(ss -tlnp 2>/dev/null | grep 9876 | grep -oP 'pid=\K[0-9]+')
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
fi

echo "=== Starting Python server ==="
nohup python3 src/server.py > /tmp/rog-py.log 2>&1 &
sleep 2

if ! ss -tlnp 2>/dev/null | grep -q 9876; then
    echo "ERROR: Python server failed to start!"
    cat /tmp/rog-py.log
    exit 1
fi
echo "Python server OK (ws://127.0.0.1:9876)"

echo "=== Starting Electron app ==="
cd /home/deepak/Documents/Projects/rog-control/desktop
export PATH="./node_modules/.bin:$PATH"
electron . 2>/tmp/rog-electron.log &
sleep 3

if ! ps aux | grep -v grep | grep -q electron; then
    echo "ERROR: Electron failed to start!"
    cat /tmp/rog-electron.log
    exit 1
fi
echo ""
echo "=== ROG Control is running! ==="
echo "  Python server log: tail -f /tmp/rog-py.log"
echo "  Electron log:       tail -f /tmp/rog-electron.log"
