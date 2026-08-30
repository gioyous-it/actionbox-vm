#!/usr/bin/env bash

set -u

DISPLAY="${DISPLAY:-:99}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

STATE_DIR="/tmp/actionboxvm"
PID_FILE="$STATE_DIR/screenshot-worker.pid"
LOG_FILE="$STATE_DIR/screenshot-worker.log"

mkdir -p "$STATE_DIR"

export DISPLAY

# --------------------------------------------------------------
# Prevent duplicate workers.
# --------------------------------------------------------------

if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"

    if [ -n "$OLD_PID" ] &&
       kill -0 "$OLD_PID" 2>/dev/null; then

        echo "Screenshot worker is already running."
        exit 0
    fi

    rm -f "$PID_FILE"
fi

# --------------------------------------------------------------
# Start the Python screenshot worker.
# --------------------------------------------------------------

nohup \
    python3 "$SCRIPT_DIR/screenshot-worker.py" \
    </dev/null \
    >>"$LOG_FILE" 2>&1 &

WORKER_PID=$!

echo "$WORKER_PID" > "$PID_FILE"

echo "ActionBoxVM screenshot worker started."
echo "PID: $WORKER_PID"
echo "DISPLAY: $DISPLAY"

exit 0