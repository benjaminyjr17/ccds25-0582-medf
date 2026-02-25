from __future__ import annotations

import math

from fastapi.testclient import TestClient

from app.main import app
from app.models import UNIFIED_DIMENSIONS
from app.routers.pareto import router as pareto_router


def test_pareto_endpoint_returns_consensus_solutions() -> None:
    if not any(route.path == "/api/pareto" for route in app.routes):
        app.include_router(pareto_router)

    payload = {
        "ai_system": {
            "id": "facerec_1",
            "name": "FaceDetect Pro v2.1",
            "description": "Law enforcement system",
            "context": {
                "dimension_scores": {
                    "transparency_explainability": 2.5,
                    "fairness_nondiscrimination": 1,
                    "safety_robustness": 5.5,
                    "privacy_data_governance": 1,
                    "human_agency_oversight": 2.5,
                    "accountability": 4.0,
                }
            },
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
        "n_solutions": 8,
        "pop_size": 32,
        "n_gen": 40,
        "seed": 7,
        "deterministic_mode": True,
    }

    with TestClient(app) as client:
        response = client.post("/api/pareto", json=payload)

    assert response.status_code == 200
    body = response.json()

    solutions = body.get("pareto_solutions")
    assert isinstance(solutions, list)
    assert 1 <= len(solutions) <= 8

    expected_dims = set(UNIFIED_DIMENSIONS)
    expected_stakeholders = set(payload["stakeholder_ids"])

    total_distances: list[float] = []
    solution_ids: list[str] = []

    for solution in solutions:
        solution_id = solution.get("solution_id")
        assert isinstance(solution_id, str)
        assert solution_id.strip() != ""
        solution_ids.append(solution_id)

        weights = solution.get("weights", {})
        assert isinstance(weights, dict)
        assert "consensus" in weights
        consensus = weights["consensus"]
        assert isinstance(consensus, dict)
        assert set(consensus.keys()) == expected_dims

        consensus_sum = sum(float(value) for value in consensus.values())
        assert math.isclose(consensus_sum, 1.0, abs_tol=0.01)

        objective_scores = solution.get("objective_scores", {})
        assert isinstance(objective_scores, dict)
        assert set(objective_scores.keys()) == expected_stakeholders

        total_distance = 0.0
        for value in objective_scores.values():
            score = float(value)
            assert score >= 0.0
            total_distance += score
        total_distances.append(total_distance)

        assert int(solution.get("rank", 0)) >= 1

    metadata = body.get("metadata", {})
    assert isinstance(metadata, dict)

    salience_vector = metadata.get("salience_vector")
    assert isinstance(salience_vector, dict)
    assert set(salience_vector.keys()) == expected_dims
    salience_sum = sum(float(value) for value in salience_vector.values())
    assert math.isclose(salience_sum, 1.0, abs_tol=1e-6)

    ablation = metadata.get("ablation_utility_by_solution")
    assert isinstance(ablation, dict)
    for solution_id in solution_ids:
        assert solution_id in ablation
        utility = float(ablation[solution_id])
        assert 0.0 <= utility <= 1.0

    if len(total_distances) >= 2:
        rounded_totals = {round(value, 10) for value in total_distances}
        assert len(rounded_totals) > 1


def test_pareto_deterministic_mode_repeatability() -> None:
    payload = {
        "ai_system": {
            "id": "facerec_1",
            "name": "FaceDetect Pro v2.1",
            "description": "Law enforcement system",
            "context": {
                "dimension_scores": {
                    "transparency_explainability": 2.5,
                    "fairness_nondiscrimination": 1,
                    "safety_robustness": 5.5,
                    "privacy_data_governance": 1,
                    "human_agency_oversight": 2.5,
                    "accountability": 4.0,
                }
            },
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
        "n_solutions": 8,
        "pop_size": 32,
        "n_gen": 40,
        "seed": 7,
        "deterministic_mode": True,
    }

    with TestClient(app) as client:
        first = client.post("/api/pareto", json=payload)
        second = client.post("/api/pareto", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()
    first_solutions = first_body.get("pareto_solutions", [])
    second_solutions = second_body.get("pareto_solutions", [])

    assert isinstance(first_solutions, list) and first_solutions
    assert isinstance(second_solutions, list) and second_solutions

    first_consensus = first_solutions[0]["weights"]["consensus"]
    second_consensus = second_solutions[0]["weights"]["consensus"]

    first_vector = tuple(round(float(first_consensus[dimension]), 4) for dimension in UNIFIED_DIMENSIONS)
    second_vector = tuple(round(float(second_consensus[dimension]), 4) for dimension in UNIFIED_DIMENSIONS)

    assert first_vector == second_vector
