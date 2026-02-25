from __future__ import annotations

import json
import math
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


DEVELOPER_WEIGHTS = {
    "transparency_explainability": 0.10,
    "fairness_nondiscrimination": 0.15,
    "safety_robustness": 0.30,
    "privacy_data_governance": 0.15,
    "human_agency_oversight": 0.15,
    "accountability": 0.15,
}


def _pretty(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, default=str)
    except Exception:
        return repr(value)


def _first_framework_id(client: TestClient) -> str:
    response = client.get("/api/frameworks")
    assert response.status_code == 200, f"GET /api/frameworks failed: {response.status_code} {response.text}"
    body = response.json()
    assert isinstance(body, list) and body, f"/api/frameworks returned no frameworks: {_pretty(body)}"
    framework = body[0]
    assert isinstance(framework, dict) and framework.get("id"), f"Invalid framework entry: {_pretty(framework)}"
    return str(framework["id"])


def _build_payload(framework_id: str, dimension_scores: dict[str, float]) -> dict[str, Any]:
    return {
        "ai_system": {
            "id": "likert_diagnostic",
            "name": "Likert Diagnostic",
            "description": "Detect current accepted score bounds.",
            "context": {"dimension_scores": dimension_scores},
        },
        "framework_ids": [framework_id],
        "stakeholder_ids": ["developer"],
        "weights": {"developer": DEVELOPER_WEIGHTS},
        "scoring_method": "topsis",
    }


def test_evaluate_accepts_boundary_scores_1_and_7() -> None:
    boundary_scores = {
        "transparency_explainability": 1.0,
        "fairness_nondiscrimination": 7.0,
        "safety_robustness": 1.0,
        "privacy_data_governance": 7.0,
        "human_agency_oversight": 1.0,
        "accountability": 7.0,
    }

    with TestClient(app) as client:
        framework_id = _first_framework_id(client)
        payload = _build_payload(framework_id, boundary_scores)
        response = client.post("/api/evaluate", json=payload)

    assert response.status_code == 200, f"Expected 200 for boundary 1/7 scores, got {response.status_code}. body={response.text}"
    body = response.json()
    overall = float(body.get("overall_score", -1.0))
    assert math.isfinite(overall), f"overall_score is not finite: {_pretty(body)}"
    assert 0.0 <= overall <= 1.0, f"overall_score out of [0,1]: overall={overall} body={_pretty(body)}"


def test_evaluate_accepts_scores_6_and_7() -> None:
    in_range_scores = {
        "transparency_explainability": 6.0,
        "fairness_nondiscrimination": 7.0,
        "safety_robustness": 6.0,
        "privacy_data_governance": 7.0,
        "human_agency_oversight": 6.0,
        "accountability": 7.0,
    }

    with TestClient(app) as client:
        framework_id = _first_framework_id(client)
        payload = _build_payload(framework_id, in_range_scores)
        response = client.post("/api/evaluate", json=payload)

    assert response.status_code == 200, (
        f"Expected 200 for scores in [6,7] under Likert 1–7. "
        f"Got {response.status_code}. body={response.text}"
    )
    body = response.json()
    overall = float(body.get("overall_score", -1.0))
    assert math.isfinite(overall), f"overall_score is not finite: {_pretty(body)}"
    assert 0.0 <= overall <= 1.0, f"overall_score out of [0,1]: overall={overall} body={_pretty(body)}"


def test_evaluate_rejects_scores_outside_1_and_7() -> None:
    out_of_range_scores = {
        "transparency_explainability": 0.0,
        "fairness_nondiscrimination": 8.0,
        "safety_robustness": 0.0,
        "privacy_data_governance": 8.0,
        "human_agency_oversight": 0.0,
        "accountability": 8.0,
    }

    with TestClient(app) as client:
        framework_id = _first_framework_id(client)
        payload = _build_payload(framework_id, out_of_range_scores)
        response = client.post("/api/evaluate", json=payload)

    assert response.status_code == 422, (
        f"Expected 422 for scores outside [1,7], got {response.status_code}. body={response.text}"
    )
