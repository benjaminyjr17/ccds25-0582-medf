#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
INITIAL_GIT_STATUS="$(git status --porcelain)"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: Neither .venv/bin/python nor python3 is available."
    exit 1
  fi
  PY="$(command -v python3)"
fi

BACKEND_PID=""
STREAMLIT_PID=""
BACKEND_LOG="$(mktemp -t medf_backend_smoke.XXXXXX.log)"
STREAMLIT_LOG="$(mktemp -t medf_streamlit_smoke.XXXXXX.log)"

cleanup() {
  local exit_code="$?"

  if [ -n "$STREAMLIT_PID" ] && kill -0 "$STREAMLIT_PID" >/dev/null 2>&1; then
    kill "$STREAMLIT_PID" >/dev/null 2>&1 || true
    wait "$STREAMLIT_PID" >/dev/null 2>&1 || true
  fi

  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi

  if [ "$exit_code" -ne 0 ]; then
    echo "RESULT: FAIL."
    echo "Backend log: $BACKEND_LOG"
    echo "Streamlit log: $STREAMLIT_LOG"
  else
    rm -f "$BACKEND_LOG" "$STREAMLIT_LOG"
  fi
}
trap cleanup EXIT

find_free_port() {
  local candidate

  for candidate in 8000 8001 8002 8003 8010; do
    if command -v lsof >/dev/null 2>&1; then
      if ! lsof -iTCP:"$candidate" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
        echo "$candidate"
        return 0
      fi
    else
      if "$PY" - "$candidate" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
      then
        echo "$candidate"
        return 0
      fi
    fi
  done

  echo "FAIL: No free port available in [8000, 8001, 8002, 8003, 8010]." >&2
  return 1
}

detect_fastapi_target() {
  local first_match
  first_match="$(rg -n --no-heading "^[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*FastAPI\\(" -g "*.py" app 2>/dev/null | head -n 1 || true)"

  if [ -z "$first_match" ]; then
    echo "app.main:app"
    return 0
  fi

  local file_path raw_assignment variable module_path
  file_path="${first_match%%:*}"
  raw_assignment="${first_match#*:*:}"
  variable="${raw_assignment%%=*}"
  variable="$(printf '%s' "$variable" | tr -d '[:space:]')"

  if [ -z "$file_path" ] || [ -z "$variable" ]; then
    echo "app.main:app"
    return 0
  fi

  module_path="${file_path%.py}"
  module_path="${module_path//\//.}"
  echo "${module_path}:${variable}"
}

wait_for_health() {
  local base_url="$1"
  local attempts=60
  local i

  for i in $(seq 1 "$attempts"); do
    if curl -sf "${base_url}/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done

  echo "FAIL: Backend health check did not become ready at ${base_url}/api/health."
  echo "Backend log tail:"
  tail -n 80 "$BACKEND_LOG" || true
  return 1
}

echo "CMD: $PY -m py_compile \$(git ls-files '*.py')"
tracked_py_files=()
while IFS= read -r path; do
  [ -f "$path" ] && tracked_py_files+=("$path")
done < <(git ls-files '*.py')

if [ "${#tracked_py_files[@]}" -eq 0 ]; then
  echo "FAIL: No tracked Python files found for py_compile."
  exit 1
fi

"$PY" -m py_compile "${tracked_py_files[@]}"
echo "PASS: py_compile."

echo "CMD: $PY -m pytest -q --strict-markers"
"$PY" -m pytest -q --strict-markers
echo "PASS: pytest."

BACKEND_PORT="$(find_free_port)"
UVICORN_TARGET="$(detect_fastapi_target)"
BASE_URL="http://127.0.0.1:${BACKEND_PORT}"
echo "Selected backend port: $BACKEND_PORT."

echo "CMD: $PY -m uvicorn $UVICORN_TARGET --port $BACKEND_PORT --log-level warning"
"$PY" -m uvicorn "$UVICORN_TARGET" --port "$BACKEND_PORT" --log-level warning >"$BACKEND_LOG" 2>&1 &
BACKEND_PID="$!"

wait_for_health "$BASE_URL"

echo "CMD: curl -s -w '\\nHTTP_STATUS:%{http_code}\\n' ${BASE_URL}/api/health"
curl -s -w "\nHTTP_STATUS:%{http_code}\n" "${BASE_URL}/api/health"
echo "PASS: backend health."

echo "CMD: BASE_URL=$BASE_URL $PY - <<'PY' (stress API calls)"
BASE_URL="$BASE_URL" "$PY" - <<'PY'
import math
import os
import statistics
import sys
import time

import requests

base_url = os.environ["BASE_URL"].rstrip("/")
iterations = 3
timeout_seconds = 180

dimension_scores = {
    "transparency_explainability": 2.5,
    "fairness_nondiscrimination": 1.0,
    "safety_robustness": 5.5,
    "privacy_data_governance": 1.0,
    "human_agency_oversight": 2.5,
    "accountability": 4.0,
}

evaluate_payload = {
    "ai_system": {
        "id": "release_smoke_eval",
        "name": "Release Smoke Evaluate",
        "description": "Deterministic release smoke evaluate payload",
        "context": {"dimension_scores": dimension_scores},
    },
    "framework_ids": ["eu_altai"],
    "stakeholder_ids": ["developer"],
    "weights": {
        "developer": {
            "transparency_explainability": 0.10,
            "fairness_nondiscrimination": 0.15,
            "safety_robustness": 0.30,
            "privacy_data_governance": 0.15,
            "human_agency_oversight": 0.15,
            "accountability": 0.15,
        }
    },
    "scoring_method": "topsis",
}

conflicts_payload = {
    "ai_system": {
        "id": "release_smoke_conflicts",
        "name": "Release Smoke Conflicts",
        "description": "Deterministic release smoke conflicts payload",
        "context": {"dimension_scores": dimension_scores},
    },
    "framework_ids": ["eu_altai"],
    "stakeholder_ids": ["developer", "regulator", "affected_community"],
}

pareto_base = {
    "ai_system": {
        "id": "release_smoke_pareto",
        "name": "Release Smoke Pareto",
        "description": "Deterministic release smoke pareto payload",
        "context": {"dimension_scores": dimension_scores},
    },
    "framework_ids": ["eu_altai"],
    "stakeholder_ids": ["developer", "regulator", "affected_community"],
    "deterministic_mode": True,
    "seed": 42,
}

pareto_high_payload = dict(pareto_base)
pareto_high_payload.update(
    {
        "n_solutions": 50,
        "pop_size": 256,
        "n_gen": 300,
    }
)

pareto_low_payload = dict(pareto_base)
pareto_low_payload.update(
    {
        "n_solutions": 8,
        "pop_size": 40,
        "n_gen": 80,
    }
)

checks = [
    (
        "evaluate",
        "/api/evaluate",
        evaluate_payload,
        {"overall_score", "framework_scores", "scoring_method"},
    ),
    (
        "conflicts",
        "/api/conflicts",
        conflicts_payload,
        {"conflicts"},
    ),
    (
        "pareto_high",
        "/api/pareto",
        pareto_high_payload,
        {"pareto_solutions"},
    ),
    (
        "pareto_low",
        "/api/pareto",
        pareto_low_payload,
        {"pareto_solutions"},
    ),
]

stats = {}

for label, endpoint, payload, required_keys in checks:
    elapsed = []
    statuses = []
    for run_index in range(iterations):
        t0 = time.perf_counter()
        response = requests.post(
            f"{base_url}{endpoint}",
            json=payload,
            timeout=timeout_seconds,
        )
        dt = time.perf_counter() - t0
        elapsed.append(dt)
        statuses.append(response.status_code)

        if response.status_code != 200:
            print(
                f"FAIL: {endpoint} run={run_index + 1}/{iterations} "
                f"status={response.status_code} body={response.text[:1600]}",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            print(
                f"FAIL: {endpoint} run={run_index + 1}/{iterations} invalid JSON: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        missing = [key for key in required_keys if key not in body]
        if missing:
            print(
                f"FAIL: {endpoint} run={run_index + 1}/{iterations} "
                f"missing keys={missing} body={body}",
                file=sys.stderr,
            )
            sys.exit(1)

        if label == "evaluate":
            overall = body.get("overall_score")
            if not isinstance(overall, (int, float)) or isinstance(overall, bool):
                print(
                    f"FAIL: /api/evaluate overall_score missing/invalid body={body}",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not math.isfinite(float(overall)):
                print(
                    f"FAIL: /api/evaluate overall_score not finite body={body}",
                    file=sys.stderr,
                )
                sys.exit(1)

    stats[label] = {
        "statuses": statuses,
        "min": min(elapsed),
        "avg": statistics.mean(elapsed),
        "max": max(elapsed),
    }

for label, values in stats.items():
    print(
        f"{label}: statuses={values['statuses']} "
        f"min={values['min']:.5f}s avg={values['avg']:.5f}s max={values['max']:.5f}s"
    )

print("PASS: deterministic stress calls.")
PY

if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
  wait "$BACKEND_PID" >/dev/null 2>&1 || true
  BACKEND_PID=""
fi

STREAMLIT_PORT="$(find_free_port)"
echo "Selected Streamlit port: $STREAMLIT_PORT."
echo "CMD: $PY -m streamlit run streamlit_app.py --server.headless true --server.port $STREAMLIT_PORT"
"$PY" -m streamlit run streamlit_app.py --server.headless true --server.port "$STREAMLIT_PORT" >"$STREAMLIT_LOG" 2>&1 &
STREAMLIT_PID="$!"

sleep 10

if ! kill -0 "$STREAMLIT_PID" >/dev/null 2>&1; then
  echo "FAIL: Streamlit process exited before smoke duration."
  echo "Streamlit log tail:"
  tail -n 80 "$STREAMLIT_LOG" || true
  exit 1
fi

if rg -n "Traceback|Exception" "$STREAMLIT_LOG" >/dev/null 2>&1; then
  echo "FAIL: Streamlit smoke log contains Traceback/Exception."
  echo "Streamlit log tail:"
  tail -n 80 "$STREAMLIT_LOG" || true
  exit 1
fi

kill "$STREAMLIT_PID" >/dev/null 2>&1 || true
wait "$STREAMLIT_PID" >/dev/null 2>&1 || true
STREAMLIT_PID=""
echo "PASS: Streamlit smoke."

echo "CMD: git status --porcelain"
CURRENT_GIT_STATUS="$(git status --porcelain)"
if [ "$CURRENT_GIT_STATUS" != "$INITIAL_GIT_STATUS" ]; then
  echo "FAIL: working tree changed during smoke run."
  echo "Initial status:"
  printf "%s\n" "$INITIAL_GIT_STATUS"
  echo "Current status:"
  printf "%s\n" "$CURRENT_GIT_STATUS"
  exit 1
fi

echo "PASS: git status unchanged by smoke run."
echo "RESULT: PASS."
