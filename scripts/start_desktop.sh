#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
BACKEND_CMD=(python -m uvicorn app.main:app --host 127.0.0.1 --port 8000)

backend_pid=""
cleanup() {
  if [[ -n "${backend_pid}" ]]; then
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Starting backend server..."
cd "$ROOT_DIR/backend"
"${BACKEND_CMD[@]}" >/tmp/pallet-manager-backend.log 2>&1 &
backend_pid=$!
sleep 1

cd "$ROOT_DIR/frontend"
echo "Launching Tauri desktop (frontend will connect to http://127.0.0.1:8000/api/v1)..."
npm run tauri dev
