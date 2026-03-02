from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = [pytest.mark.extreme, pytest.mark.stress]


DIMENSION_SCORES = {
    "transparency_explainability": 2.5,
    "fairness_nondiscrimination": 1.0,
    "safety_robustness": 5.5,
    "privacy_data_governance": 1.0,
    "human_agency_oversight": 2.5,
    "accountability": 4.0,
}

SEEDS = [42, 20260302, 314159]


def _payload_for_seed(seed: int) -> dict[str, Any]:
    return {
        "ai_system": {
            "id": f"extreme_pareto_{seed}",
            "name": "Extreme Pareto Boundary",
            "description": "Boundary stress payload",
            "context": {"dimension_scores": DIMENSION_SCORES},
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
        "n_solutions": 50,
        "pop_size": 256,
        "n_gen": 300,
        "seed": seed,
        "deterministic_mode": True,
    }


def _canonical_signature(
    response_body: Any,
) -> tuple[tuple[tuple[str, float], tuple[tuple[str, float], ...]], ...]:
    assert isinstance(response_body, dict)
    solutions = response_body.get("pareto_solutions", [])
    assert isinstance(solutions, list)

    canonical: list[tuple[tuple[str, float], tuple[tuple[str, float], ...]]] = []
    for solution in solutions:
        if not isinstance(solution, dict):
            continue
        objective_scores = solution.get("objective_scores", {})
        if not isinstance(objective_scores, dict):
            continue
        weights = solution.get("weights", {})
        consensus = weights.get("consensus", {}) if isinstance(weights, dict) else {}
        if not isinstance(consensus, dict):
            continue

        objective_signature = tuple(
            (str(key), round(float(value), 8))
            for key, value in sorted(objective_scores.items())
        )
        consensus_signature = tuple(
            (str(key), round(float(value), 8))
            for key, value in sorted(consensus.items())
        )
        canonical.append((objective_signature, consensus_signature))

    return tuple(sorted(canonical))


def test_extreme_pareto_boundary_runs_are_repeatable_per_seed() -> None:
    with TestClient(app) as client:
        for seed in SEEDS:
            payload = _payload_for_seed(seed)

            first = client.post("/api/pareto", json=deepcopy(payload))
            second = client.post("/api/pareto", json=deepcopy(payload))

            assert first.status_code == 200
            assert second.status_code == 200

            first_body = first.json()
            second_body = second.json()

            first_solutions = first_body.get("pareto_solutions", [])
            second_solutions = second_body.get("pareto_solutions", [])

            assert isinstance(first_solutions, list) and first_solutions
            assert isinstance(second_solutions, list) and second_solutions
            assert len(first_solutions) <= payload["n_solutions"]
            assert len(second_solutions) <= payload["n_solutions"]

            assert _canonical_signature(first_body) == _canonical_signature(second_body)
