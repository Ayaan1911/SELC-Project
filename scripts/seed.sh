#!/usr/bin/env bash
# Install dependencies (first run) and reset the DB with demo data.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm install --no-audit --no-fund)
fi

if [ ! -f "$ROOT/backend/.env" ]; then
  echo "Generating backend/.env with a random JWT secret (see backend/.env.example)"
  SECRET="$("$ROOT/.venv/bin/python" -c 'import secrets; print(secrets.token_hex(32))')"
  echo "SECURECART_JWT_SECRET=$SECRET" > "$ROOT/backend/.env"
fi

cd "$ROOT/backend"
"$ROOT/.venv/bin/python" seed.py
