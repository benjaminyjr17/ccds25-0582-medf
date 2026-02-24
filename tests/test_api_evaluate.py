from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models import UNIFIED_DIMENSIONS
from app.routers.evaluate import router as evaluate_router


def test_evaluate_topsis_with_dimension_scores_context() -> None:
    if not any(route.path == "/api/evaluate" for route in app.routes):
        app.include_router(evaluate_router)

    payload = {
        "ai_system": {
            "id": "facial_rec_system",
            "name": "Facial Recognition",
            "description": "Stage 2 integration test system",
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
        response = client.post("/api/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert 0.0 <= float(body["overall_score"]) <= 1.0
    assert len(body["framework_scores"]) == 1

    framework_score = body["framework_scores"][0]
    assert isinstance(framework_score["dimension_scores"], dict)
    assert set(framework_score["dimension_scores"].keys()) == set(UNIFIED_DIMENSIONS)
