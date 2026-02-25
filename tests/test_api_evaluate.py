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


def test_evaluate_scores_differ_across_frameworks_with_framework_default_weights() -> None:
    if not any(route.path == "/api/evaluate" for route in app.routes):
        app.include_router(evaluate_router)

    base_payload = {
        "ai_system": {
            "id": "facial_rec_system",
            "name": "Facial Recognition",
            "description": "Framework sensitivity integration test",
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
        "framework_ids": [],
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
        frameworks_response = client.get("/api/frameworks")
        assert frameworks_response.status_code == 200
        frameworks = frameworks_response.json()
        framework_ids = [framework["id"] for framework in frameworks]
        assert len(framework_ids) >= 2

        weight_vectors_by_framework: dict[str, tuple[float, ...]] = {}
        for framework in frameworks:
            framework_dimension_map = {
                dimension["name"]: float(dimension["weight_default"])
                for dimension in framework["dimensions"]
            }
            weight_vectors_by_framework[framework["id"]] = tuple(
                framework_dimension_map[dimension] for dimension in UNIFIED_DIMENSIONS
            )

        framework_one = framework_ids[0]
        framework_two = framework_ids[1]

        payload_one = dict(base_payload)
        payload_one["framework_ids"] = [framework_one]
        response_one = client.post("/api/evaluate", json=payload_one)
        assert response_one.status_code == 200
        score_one = float(response_one.json()["overall_score"])

        payload_two = dict(base_payload)
        payload_two["framework_ids"] = [framework_two]
        response_two = client.post("/api/evaluate", json=payload_two)
        assert response_two.status_code == 200
        score_two = float(response_two.json()["overall_score"])

    assert abs(score_one - score_two) > 1e-9, (
        "Framework-aware weighting did not change score. "
        f"{framework_one} weights={weight_vectors_by_framework[framework_one]}, "
        f"{framework_two} weights={weight_vectors_by_framework[framework_two]}, "
        f"scores=({score_one}, {score_two})"
    )
