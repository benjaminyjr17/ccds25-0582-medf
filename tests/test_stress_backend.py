from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS
from tests.test_release_candidate_invariants import (
    assert_json_no_nan_inf,
    assert_rho_bounds,
    assert_score_bounds,
)
from tests.test_release_candidate_stress import (
    _conflicts_payload,
    _default_weights_from_stakeholders,
    _evaluate_payload,
    _get_framework_ids,
)

DIMENSIONS = list(UNIFIED_DIMENSIONS)
STAKEHOLDERS = ["developer", "regulator", "affected_community"]


def _json_or_text(response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"non_json_body": response.text}


def _score_map(rng: random.Random) -> dict[str, float]:
    return {
        dimension: float(rng.uniform(LIKERT_MIN, LIKERT_MAX))
        for dimension in DIMENSIONS
    }


def test_seeded_backend_stress_stability() -> None:
    rng = random.Random(1337)
    evaluate_runs = 400
    conflict_runs = 150

    with TestClient(app) as client:
        framework_id = _get_framework_ids(client)[0]
        baseline_weights = _default_weights_from_stakeholders(client, STAKEHOLDERS)

        for run_index in range(evaluate_runs):
            payload = _evaluate_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                weights=baseline_weights,
                score_map=_score_map(rng),
            )
            response = client.post("/api/evaluate", json=payload)
            response_json = _json_or_text(response)
            context = (
                "endpoint=/api/evaluate "
                f"seed=1337 run={run_index + 1}/{evaluate_runs} framework={framework_id}"
            )
            assert response.status_code == 200, (
                f"{context} status={response.status_code} response={response_json!r}"
            )
            assert isinstance(response_json, Mapping), (
                f"{context} expected mapping response, got {type(response_json)!r}"
            )
            assert "framework_scores" in response_json or "overall_score" in response_json, (
                f"{context} missing expected scoring keys. response={response_json!r}"
            )
            assert_json_no_nan_inf(response_json, context=context)
            assert_score_bounds(response_json, context=context)

        for run_index in range(conflict_runs):
            payload = _conflicts_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                score_map=_score_map(rng),
            )
            response = client.post("/api/conflicts", json=payload)
            response_json = _json_or_text(response)
            context = (
                "endpoint=/api/conflicts "
                f"seed=1337 run={run_index + 1}/{conflict_runs} framework={framework_id}"
            )
            assert response.status_code == 200, (
                f"{context} status={response.status_code} response={response_json!r}"
            )
            assert isinstance(response_json, Mapping), (
                f"{context} expected mapping response, got {type(response_json)!r}"
            )
            assert "conflicts" in response_json, (
                f"{context} missing 'conflicts' key. response={response_json!r}"
            )
            assert_json_no_nan_inf(response_json, context=context)
            assert_rho_bounds(response_json, context=context)
