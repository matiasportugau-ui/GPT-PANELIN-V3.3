#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a; source .env; set +a
fi

export PYTHONPATH="${SCRIPT_DIR}/src"
export IDEMPOTENCY_BACKEND=memory
export PANELIN_ORCH_API_KEY="${PANELIN_ORCH_API_KEY:-test-key-123}"

echo "Running tests ..."
python -m pytest tests/ -v --tb=short "$@"
