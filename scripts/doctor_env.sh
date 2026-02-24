#!/usr/bin/env bash

set -u

fix_line="Run: source .venv/bin/activate && python -m pip install -r requirements.txt"

fail() {
  echo "[FAIL] $1"
  echo "${fix_line}"
  exit 1
}

python_path="$(command -v python 2>/dev/null || true)"
if [ -z "${python_path}" ]; then
  fail "python not found in PATH"
fi

echo "python path: ${python_path}"
if python -c "import sys; print('sys.executable', sys.executable)"; then
  echo "[PASS] resolved interpreter"
else
  fail "unable to read sys.executable"
fi

if python -c "import fastapi; print('fastapi ok', fastapi.__version__)"; then
  echo "[PASS] fastapi import"
else
  fail "fastapi import failed"
fi

if python -c "from app.main import app; print('import app.main ok')"; then
  echo "[PASS] app.main import"
else
  fail "app.main import failed"
fi

echo "[PASS] doctor complete"
