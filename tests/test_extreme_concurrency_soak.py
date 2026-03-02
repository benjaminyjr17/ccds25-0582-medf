from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = [pytest.mark.extreme, pytest.mark.soak, pytest.mark.stress]


DIMENSION_SCORES = {
    "transparency_explainability": 2.5,
    "fairness_nondiscrimination": 1.0,
    "safety_robustness": 5.5,
    "privacy_data_governance": 1.0,
    "human_agency_oversight": 2.5,
    "accountability": 4.0,
}

EVALUATE_PAYLOAD = {
    "ai_system": {
        "id": "extreme_soak_eval",
        "name": "Extreme Soak Evaluate",
        "description": "Extreme concurrency soak payload",
        "context": {"dimension_scores": DIMENSION_SCORES},
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

CONFLICTS_PAYLOAD = {
    "framework_ids": ["eu_altai"],
    "stakeholder_ids": ["developer", "regulator", "affected_community"],
    "ai_system": {
        "id": "extreme_soak_conflicts",
        "name": "Extreme Soak Conflicts",
        "description": "Extreme concurrency soak payload",
        "context": {"dimension_scores": DIMENSION_SCORES},
    },
}

PARETO_LOW_PAYLOAD = {
    "ai_system": {
        "id": "extreme_soak_pareto",
        "name": "Extreme Soak Pareto",
        "description": "Extreme concurrency soak payload",
        "context": {"dimension_scores": DIMENSION_SCORES},
    },
    "framework_ids": ["eu_altai"],
    "stakeholder_ids": ["developer", "regulator", "affected_community"],
    "n_solutions": 8,
    "pop_size": 40,
    "n_gen": 80,
    "seed": 42,
    "deterministic_mode": True,
}


def _request_once(endpoint: str, payload: dict[str, Any]) -> tuple[str, int, Any]:
    with TestClient(app) as client:
        response = client.post(endpoint, json=payload)
    try:
        body = response.json()
    except Exception:
        body = None
    return endpoint, response.status_code, body


def _pareto_signature(response_body: Any) -> tuple[tuple[tuple[str, float], ...], ...]:
    assert isinstance(response_body, dict)
    solutions = response_body.get("pareto_solutions", [])
    assert isinstance(solutions, list)

    canonical: list[tuple[tuple[str, float], ...]] = []
    for item in solutions:
        if not isinstance(item, dict):
            continue
        objective_scores = item.get("objective_scores", {})
        if not isinstance(objective_scores, dict):
            continue

        objective_tuple = tuple(
            (str(key), round(float(value), 8))
            for key, value in sorted(objective_scores.items())
        )
        canonical.append(objective_tuple)

    return tuple(sorted(canonical))


def test_threaded_mixed_endpoint_barrage_has_no_5xx_or_malformed_json() -> None:
    jobs: list[tuple[str, dict[str, Any]]] = []
    for _ in range(24):
        jobs.append(("/api/evaluate", deepcopy(EVALUATE_PAYLOAD)))
        jobs.append(("/api/conflicts", deepcopy(CONFLICTS_PAYLOAD)))
        jobs.append(("/api/pareto", deepcopy(PARETO_LOW_PAYLOAD)))

    results: list[tuple[str, int, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(_request_once, endpoint, payload) for endpoint, payload in jobs]
        for future in as_completed(futures):
            results.append(future.result())

    assert len(results) == len(jobs)
    for endpoint, status_code, body in results:
        assert status_code < 500, f"{endpoint} returned {status_code}"
        assert body is not None, f"{endpoint} returned non-JSON body"


def test_deterministic_mode_repeatability_after_soak_subset() -> None:
    with TestClient(app) as client:
        first = client.post("/api/pareto", json=deepcopy(PARETO_LOW_PAYLOAD))
        second = client.post("/api/pareto", json=deepcopy(PARETO_LOW_PAYLOAD))

    assert first.status_code == 200
    assert second.status_code == 200

    first_sig = _pareto_signature(first.json())
    second_sig = _pareto_signature(second.json())

    assert first_sig
    assert first_sig == second_sig
