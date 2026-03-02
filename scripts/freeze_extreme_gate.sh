#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "FAIL: Neither .venv/bin/python nor python3 is available."
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "FAIL: Working tree is dirty. Commit or stash changes before freeze gate."
  exit 1
fi

echo "=== FAST GATE ==="
echo "CMD: $PY -m pytest -q --strict-markers -m \"not extreme and not property and not soak\""
"$PY" -m pytest -q --strict-markers -m "not extreme and not property and not soak"
echo "PASS: fast gate."

echo "=== HEAVY MARKER GATE ==="
echo "CMD: MEDF_EXTREME=1 $PY -m pytest -q --strict-markers -m \"extreme or property or soak\""
MEDF_EXTREME=1 "$PY" -m pytest -q --strict-markers -m "extreme or property or soak"
echo "PASS: heavy marker gate."

echo "=== COVERAGE GATE ==="
echo "CMD: MEDF_EXTREME=1 $PY -m pytest -q --strict-markers --cov=app --cov-branch --cov-report=term-missing:skip-covered --cov-report=json:coverage.json --cov-fail-under=88"
MEDF_EXTREME=1 "$PY" -m pytest -q --strict-markers \
  --cov=app \
  --cov-branch \
  --cov-report=term-missing:skip-covered \
  --cov-report=json:coverage.json \
  --cov-fail-under=88

echo "CMD: module coverage thresholds"
"$PY" - <<'PY'
import json
import sys
from pathlib import PurePosixPath

thresholds = {
    "app/routers/evaluate.py": 95.0,
    "app/routers/conflicts.py": 95.0,
    "app/routers/pareto.py": 93.0,
    "app/scoring_engine.py": 97.0,
    "app/framework_registry.py": 92.0,
    "app/harm_assessment.py": 95.0,
    "app/database.py": 90.0,
    "app/conflict_detection.py": 90.0,
}

with open("coverage.json", "r", encoding="utf-8") as handle:
    payload = json.load(handle)

files = payload.get("files", {})
normalized = {
    str(PurePosixPath(path.replace("\\", "/"))): data
    for path, data in files.items()
}

def summary_for(target: str):
    for path, data in normalized.items():
        if path.endswith(target):
            return data.get("summary", {})
    return None

failures = []
for target, minimum in thresholds.items():
    summary = summary_for(target)
    if summary is None:
        failures.append(f"Missing coverage entry for {target}")
        continue
    percent = float(summary.get("percent_covered", 0.0))
    if percent < minimum:
        failures.append(f"{target}: {percent:.2f}% < required {minimum:.2f}%")
    else:
        print(f"PASS {target}: {percent:.2f}% >= {minimum:.2f}%")

if failures:
    print("Coverage threshold failures:")
    for item in failures:
        print(f"- {item}")
    sys.exit(1)
PY
echo "PASS: coverage gate."

echo "=== RELEASE SMOKE ==="
echo "CMD: bash scripts/release_smoke.sh"
bash scripts/release_smoke.sh
echo "PASS: release smoke."

if [ -n "$(git status --porcelain)" ]; then
  echo "FAIL: Working tree changed during freeze gate."
  exit 1
fi

echo "PASS: working tree clean."
echo "RESULT: PASS."
