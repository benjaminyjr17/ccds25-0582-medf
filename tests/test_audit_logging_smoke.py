from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def test_evaluate_writes_audit_log_line() -> None:
    log_dir = Path("data") / "audit_logs"
    log_file = log_dir / "audit.jsonl"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        probe = log_dir / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        pytest.skip("Filesystem not writable for audit log smoke test.")

    before_lines = _read_lines(log_file)

    payload = {
        "ai_system": {
            "id": "audit_smoke_system",
            "name": "Audit Smoke System",
            "description": "Smoke test input",
            "context": {
                "dimension_scores": {
                    "transparency_explainability": 2,
                    "fairness_nondiscrimination": 1,
                    "safety_robustness": 4,
                    "privacy_data_governance": 1,
                    "human_agency_oversight": 2,
                    "accountability": 3,
                }
            },
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

    with TestClient(app) as client:
        health_response = client.get("/api/health")
        assert health_response.status_code == 200

        mid_lines = _read_lines(log_file)
        assert len(mid_lines) == len(before_lines)

        evaluate_response = client.post("/api/evaluate", json=payload)
        assert evaluate_response.status_code == 200

    after_lines = _read_lines(log_file)
    assert len(after_lines) >= len(mid_lines) + 1

    last_record = json.loads(after_lines[-1])
    assert last_record.get("endpoint_path") == "/api/evaluate"
    assert "run_id" in last_record
    assert last_record.get("run_id")
