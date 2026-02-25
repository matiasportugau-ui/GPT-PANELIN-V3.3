#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a; source .env; set +a
fi

export PYTHONPATH="${SCRIPT_DIR}/src"

echo "Starting Panelin Sheets Orchestrator (dev) on http://localhost:8080 ..."
uvicorn panelin_sheets_orchestrator.service:app \
  --host 0.0.0.0 \
  --port 8080 \
  --reload \
  --reload-dir src
