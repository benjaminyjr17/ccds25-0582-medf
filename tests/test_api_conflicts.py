from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.routers.conflicts import router as conflicts_router


def test_conflicts_endpoint_returns_pairwise_spearman_results() -> None:
    if not any(route.path == "/api/conflicts" for route in app.routes):
        app.include_router(conflicts_router)

    payload = {
        "ai_system": {
            "id": "facial_rec_system",
            "name": "Facial Recognition",
            "description": "Stage 2 conflicts integration test system",
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
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
    }

    with TestClient(app) as client:
        response = client.post("/api/conflicts", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert isinstance(body.get("conflicts"), list)
    assert len(body["conflicts"]) == 3

    allowed_levels = {"low", "moderate", "high"}
    for item in body["conflicts"]:
        assert -1.0 <= float(item["spearman_rho"]) <= 1.0
        assert item["conflict_level"] in allowed_levels

    metadata = body.get("metadata", {})
    assert "correlation_matrix" in metadata
    assert "stakeholder_rankings" in metadata
