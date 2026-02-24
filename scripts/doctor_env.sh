#!/usr/bin/env bash

set -u

fix_line="Run: source .venv/bin/activate && python -m pip install -r requirements.txt"
VENV_PY="$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python"

fail() {
  echo "[FAIL] $1"
  echo "${fix_line}"
  exit 1
}

if [ ! -x "${VENV_PY}" ]; then
  fail "venv python not found at ${VENV_PY}"
fi

echo "venv python: ${VENV_PY}"
if "${VENV_PY}" -c "import sys; print('sys.executable', sys.executable)"; then
  echo "[PASS] resolved interpreter"
else
  fail "unable to read sys.executable"
fi

if "${VENV_PY}" -c "import fastapi; print('fastapi ok', fastapi.__version__)"; then
  echo "[PASS] fastapi import"
else
  fail "fastapi import failed"
fi

if "${VENV_PY}" -c "from app.main import app; print('import app.main ok')"; then
  echo "[PASS] app.main import"
else
  fail "app.main import failed"
fi

echo "[PASS] doctor complete"
