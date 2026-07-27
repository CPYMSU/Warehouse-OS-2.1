#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
VENV="$BACKEND/.venv"
PORT="${WAREHOUSE_PORT:-8080}"
HOST="${WAREHOUSE_HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if command -v curl >/dev/null 2>&1; then
  headers="$(curl -sS -D - -o /dev/null --max-time 2 "http://${HOST}:${PORT}/health" || true)"
  if [[ -n "$headers" ]]; then
    if grep -qi '^X-Warehouse-Backend: fastapi-postgresql' <<<"$headers"; then
      echo "Warehouse OS backend is already running at http://${HOST}:${PORT}"
      exit 0
    fi
    echo "Port ${PORT} is occupied by a non-Warehouse backend (usually a static file server)." >&2
    echo "Stop that process, then run this script again. /api requests must be served by FastAPI." >&2
    exit 1
  fi
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

"$VENV/bin/pip" install -e "${BACKEND}[dev]"

if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo "Created backend/.env from the local template."
fi

if [[ "${WAREHOUSE_SKIP_DOCKER:-0}" != "1" ]] && command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$ROOT/compose.yaml" up -d postgres
  fi
fi

cd "$BACKEND"
attempt=1
until "$VENV/bin/alembic" upgrade head; do
  if (( attempt >= 20 )); then
    echo "PostgreSQL did not become ready after ${attempt} migration attempts." >&2
    exit 1
  fi
  echo "Waiting for PostgreSQL (${attempt}/20)…"
  attempt=$((attempt + 1))
  sleep 2
done

args=(app.main:app --host "$HOST" --port "$PORT" --app-dir "$BACKEND")
if [[ "${WAREHOUSE_RELOAD:-1}" == "1" ]]; then
  args+=(--reload)
fi

echo "Starting Warehouse OS 2.1 full stack at http://${HOST}:${PORT}"
echo "Frontend, API and PostgreSQL now share the governed FastAPI entry point."
exec "$VENV/bin/uvicorn" "${args[@]}"
