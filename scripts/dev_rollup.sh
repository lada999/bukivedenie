#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

PYTHON_CMD=${PYTHON_CMD:-python}
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_LOG="$ROOT_DIR/logs/backend-dev.log"
ROLLUP_LOG="$ROOT_DIR/logs/rollup-dev.log"

mkdir -p "$ROOT_DIR/logs"

pids=()

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

# Start rollup watcher
if [ -d "$FRONTEND_DIR" ]; then
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    echo "Starting rollup watcher (cd $FRONTEND_DIR && npm run dev)"
    ( cd "$FRONTEND_DIR" && npm run dev 2>&1 ) > "$ROLLUP_LOG" 2>&1 &
    pid_rollup=$!
    pids+=("$pid_rollup")
    echo "Rollup PID=$pid_rollup, log=$ROLLUP_LOG"
  else
    echo "Node/npm not found; cannot start rollup watcher" >&2
  fi
else
  echo "Frontend directory not found: $FRONTEND_DIR" >&2
fi

# Tail logs
if command -v tail >/dev/null 2>&1; then
  touch "$BACKEND_LOG" "$ROLLUP_LOG"
  tail -F "$BACKEND_LOG" "$ROLLUP_LOG" &
  tail_pid=$!
  pids+=("$tail_pid")
fi

wait
cleanup
