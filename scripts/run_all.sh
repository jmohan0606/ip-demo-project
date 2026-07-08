#!/usr/bin/env bash
# Combined launcher: starts the FastAPI backend (port 8000) AND the Next.js frontend
# (port 3000) together, with the correct env, and streams both logs. Ctrl-C stops both.
#
# Runner selection: uses `uv run` when uv is installed (the client/standard path); otherwise
# falls back to the interpreter on PATH (`python -m uvicorn`) so it also works in a
# pre-provisioned environment (e.g. this Codespace) where uv is not installed.
#
# Env is read from .env (backend) and frontend/.env.local (frontend) by the apps themselves;
# the two host/port vars below only pick where each server binds.
set -euo pipefail
cd "$(dirname "$0")/.."

API_HOST="${API_HOST:-0.0.0.0}"   # 0.0.0.0 so the Codespaces forwarder / browser can reach it
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-3000}"

if command -v uv >/dev/null 2>&1; then
  BACKEND_CMD=(uv run uvicorn app.api.main:app --reload --host "$API_HOST" --port "$API_PORT")
else
  echo "[run_all] uv not found — using 'python -m uvicorn' (ambient interpreter)."
  BACKEND_CMD=(python -m uvicorn app.api.main:app --reload --host "$API_HOST" --port "$API_PORT")
fi

echo "[run_all] backend  -> http://${API_HOST}:${API_PORT}  (docs: /docs)"
echo "[run_all] frontend -> http://localhost:${UI_PORT}"

PIDS=()
cleanup() { echo; echo "[run_all] stopping…"; for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup INT TERM EXIT

"${BACKEND_CMD[@]}" & PIDS+=("$!")
# `-- -p $UI_PORT` overrides the package.json default (`next dev -p 3000`).
( cd frontend && npm run dev -- -p "$UI_PORT" ) & PIDS+=("$!")

wait
