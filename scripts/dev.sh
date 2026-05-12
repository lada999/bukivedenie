#!/usr/bin/env bash
# Start backend and frontend dev servers and forward signals to children.
# Usage: ./scripts/dev.sh
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

PYTHON_CMD=${PYTHON_CMD:-python}
FRONTEND_DIR="$ROOT_DIR/frontend"
FRONTEND_NODE_MODULES="$FRONTEND_DIR/node_modules"
BACKEND_LOG="$ROOT_DIR/logs/backend-dev.log"
FRONTEND_LOG="$ROOT_DIR/logs/frontend-dev.log"

command -v nc >/dev/null 2>&1 || true

wait_for_port() {
  host=$1
  port=$2
  for _ in {1..60}; do
    if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

mkdir -p "$ROOT_DIR/logs"

pids=()

cleanup() {
  echo "Stopping children..."
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
    fi
  done
  wait 2>/dev/null || true
  exit 0
}

trap cleanup INT TERM

# Start backend
echo "Starting backend: $PYTHON_CMD -m src.webapp --host 127.0.0.1 --port 8000"
( $PYTHON_CMD -m src.webapp --host 127.0.0.1 --port 8000 ) > "$BACKEND_LOG" 2>&1 &
pid_backend=$!
pids+=("$pid_backend")
echo "Backend PID=$pid_backend, log=$BACKEND_LOG"

echo "Waiting for backend to be ready..."
wait_for_port 127.0.0.1 8000 || echo "Backend readiness check timed out; continuing"

# Start frontend watcher with Rollup live-reload; fallback to browser-sync or local python dev server
if [ -d "$FRONTEND_DIR" ]; then
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    echo "Node detected. Starting frontend watcher (skip dependency install if node_modules already exists) in $FRONTEND_DIR"
    (
      cd "$FRONTEND_DIR" || exit 1

      # Dependencies are expected to be installed via make dev-setup.
      # Keep dev-all fast: do not auto-install here.
      if [ ! -d "$FRONTEND_NODE_MODULES" ] || [ ! -x "$FRONTEND_NODE_MODULES/.bin/rollup" ]; then
        echo "frontend/node_modules missing or rollup not found. Run: make frontend-install" >&2
      else
        echo "Dependencies present in frontend/node_modules; skipping npm install"
      fi

      # start rollup watcher if available, otherwise try browser-sync fallback
      npm run dev || npm run dev:bs || exit 1
    ) > "$FRONTEND_LOG" 2>&1 &
    pid_frontend=$!
    pids+=("$pid_frontend")
    echo "Frontend PID=$pid_frontend, log=$FRONTEND_LOG"
    # short wait to detect fast failures
    sleep 2
    if ! kill -0 "$pid_frontend" 2>/dev/null; then
      echo "Frontend watcher failed to start or exited quickly. Falling back to python dev proxy. Check $FRONTEND_LOG" >&2
      # start python fallback dev server
      ( "$PYTHON_CMD" "$ROOT_DIR/scripts/dev_local.py" ) > "$FRONTEND_LOG" 2>&1 &
      pid_fallback=$!
      pids+=("$pid_fallback")
      echo "Fallback dev server PID=$pid_fallback, log=$FRONTEND_LOG"
    fi
  else
    echo "Node/npm not available; starting python dev proxy server"
    ( "$PYTHON_CMD" "$ROOT_DIR/scripts/dev_local.py" ) > "$FRONTEND_LOG" 2>&1 &
    pid_fallback=$!
    pids+=("$pid_fallback")
    echo "Fallback dev server PID=$pid_fallback, log=$FRONTEND_LOG"
  fi
else
  echo "Frontend dir not found: $FRONTEND_DIR" >&2
fi

# Tail logs (both) in foreground when available
if command -v tail >/dev/null 2>&1; then
  echo "Tailing logs. Press Ctrl-C to stop."
  touch "$BACKEND_LOG" "$FRONTEND_LOG"
  tail -F "$BACKEND_LOG" "$FRONTEND_LOG" &
  tail_pid=$!
  pids+=("$tail_pid")
fi

# Wait for children
wait
cleanup
