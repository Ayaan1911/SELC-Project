#!/usr/bin/env bash
# Start backend (127.0.0.1:8000) and frontend (127.0.0.1:5173). Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$ROOT/backend/securecart.db" ] || [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "First run: installing dependencies and seeding the database..."
  "$ROOT/scripts/seed.sh"
fi

cleanup() { kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$ROOT/backend" && "$ROOT/.venv/bin/python" app.py) &
BACKEND_PID=$!

(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

echo
echo "SecureCart v1 (INTENTIONALLY VULNERABLE) - localhost only"
echo "  Frontend: http://127.0.0.1:5173"
echo "  Backend:  http://127.0.0.1:8000  (docs at /docs)"
echo

wait
