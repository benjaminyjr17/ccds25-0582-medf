from __future__ import annotations

import pytest
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


def test_evaluate_score_differs_across_frameworks() -> None:
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

        weight_vectors_by_framework = {}
        for framework in frameworks:
            framework_dimension_map = {
                dimension["name"]: float(dimension["weight_default"])
                for dimension in framework["dimensions"]
            }
            weight_vectors_by_framework[framework["id"]] = tuple(
                framework_dimension_map[dimension] for dimension in UNIFIED_DIMENSIONS
            )

        selected_pair: tuple[str, str] | None = None
        for index, framework_id_a in enumerate(framework_ids):
            for framework_id_b in framework_ids[index + 1:]:
                vector_a = weight_vectors_by_framework[framework_id_a]
                vector_b = weight_vectors_by_framework[framework_id_b]
                if any(abs(a - b) > 1e-12 for a, b in zip(vector_a, vector_b)):
                    selected_pair = (framework_id_a, framework_id_b)
                    break
            if selected_pair is not None:
                break

        if selected_pair is None:
            pytest.skip(
                "No framework pair with distinct weight_default vectors; cannot assert score divergence."
            )

        payload_one = dict(base_payload)
        payload_one["framework_ids"] = [selected_pair[0]]
        response_one = client.post("/api/evaluate", json=payload_one)
        assert response_one.status_code == 200
        score_one = float(response_one.json()["overall_score"])

        payload_two = dict(base_payload)
        payload_two["framework_ids"] = [selected_pair[1]]
        response_two = client.post("/api/evaluate", json=payload_two)
        assert response_two.status_code == 200
        score_two = float(response_two.json()["overall_score"])

    assert abs(score_one - score_two) > 1e-9
