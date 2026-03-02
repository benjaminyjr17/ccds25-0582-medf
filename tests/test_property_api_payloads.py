from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from app.main import app
from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS


pytestmark = [pytest.mark.extreme, pytest.mark.property]

DIMENSIONS = tuple(UNIFIED_DIMENSIONS)
DEFAULT_STAKEHOLDERS = ["developer", "regulator", "affected_community"]


def _normalize_weights(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    normalized = array / float(np.sum(array))
    return {
        dimension: float(normalized[index])
        for index, dimension in enumerate(DIMENSIONS)
    }


def _assert_no_nan_inf(payload: Any) -> None:
    if isinstance(payload, dict):
        for value in payload.values():
            _assert_no_nan_inf(value)
        return
    if isinstance(payload, list):
        for item in payload:
            _assert_no_nan_inf(item)
        return
    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        assert math.isfinite(float(payload))


def _detail_shape(response_body: dict[str, Any]) -> tuple[str, ...]:
    detail = response_body.get("detail")
    if isinstance(detail, list):
        return ("list", str(len(detail)))
    if isinstance(detail, dict):
        return ("dict",)
    return (type(detail).__name__,)


_dimension_scores_strategy = st.fixed_dictionaries(
    {
        dimension: st.floats(
            min_value=LIKERT_MIN,
            max_value=LIKERT_MAX,
            allow_nan=False,
            allow_infinity=False,
        )
        for dimension in DIMENSIONS
    }
)

_weight_vector_strategy = st.lists(
    st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False),
    min_size=len(DIMENSIONS),
    max_size=len(DIMENSIONS),
).map(_normalize_weights)


@given(
    dimension_scores=_dimension_scores_strategy,
    weights=_weight_vector_strategy,
    method=st.sampled_from(["topsis", "wsm"]),
)
@settings(max_examples=25)
def test_property_evaluate_valid_payloads_return_finite_json(
    dimension_scores: dict[str, float],
    weights: dict[str, float],
    method: str,
) -> None:
    payload = {
        "ai_system": {
            "id": "property_eval",
            "name": "Property Evaluate",
            "description": "Property test payload",
            "context": {"dimension_scores": dimension_scores},
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer"],
        "weights": {"developer": weights},
        "scoring_method": method,
    }

    with TestClient(app) as client:
        response = client.post("/api/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    _assert_no_nan_inf(body)


@given(dimension_scores=_dimension_scores_strategy)
@settings(max_examples=25)
def test_property_conflicts_valid_payloads_return_finite_json(
    dimension_scores: dict[str, float],
) -> None:
    payload = {
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": DEFAULT_STAKEHOLDERS,
        "ai_system": {
            "id": "property_conflicts",
            "name": "Property Conflicts",
            "description": "Property test payload",
            "context": {"dimension_scores": dimension_scores},
        },
    }

    with TestClient(app) as client:
        response = client.post("/api/conflicts", json=payload)

    assert response.status_code == 200
    body = response.json()
    _assert_no_nan_inf(body)


@given(
    dimension_scores=_dimension_scores_strategy,
    n_solutions=st.integers(min_value=5, max_value=12),
    pop_size=st.integers(min_value=20, max_value=40),
    n_gen=st.integers(min_value=20, max_value=60),
    seed=st.integers(min_value=1, max_value=10_000),
)
@settings(max_examples=8)
def test_property_pareto_valid_payloads_return_finite_json(
    dimension_scores: dict[str, float],
    n_solutions: int,
    pop_size: int,
    n_gen: int,
    seed: int,
) -> None:
    payload = {
        "ai_system": {
            "id": "property_pareto",
            "name": "Property Pareto",
            "description": "Property test payload",
            "context": {"dimension_scores": dimension_scores},
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": DEFAULT_STAKEHOLDERS,
        "n_solutions": n_solutions,
        "pop_size": pop_size,
        "n_gen": n_gen,
        "seed": seed,
        "deterministic_mode": True,
    }

    with TestClient(app) as client:
        response = client.post("/api/pareto", json=payload)

    assert response.status_code == 200
    body = response.json()
    _assert_no_nan_inf(body)
    assert isinstance(body.get("pareto_solutions"), list)


@pytest.mark.extreme
def test_invalid_payload_mutations_return_deterministic_422_shape() -> None:
    evaluate_base = {
        "ai_system": {
            "id": "invalid_eval",
            "name": "Invalid Evaluate",
            "description": "Mutation",
            "context": {
                "dimension_scores": {
                    "transparency_explainability": 2.0,
                    "fairness_nondiscrimination": 2.0,
                    "safety_robustness": 2.0,
                    "privacy_data_governance": 2.0,
                    "human_agency_oversight": 2.0,
                    "accountability": 2.0,
                }
            },
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer"],
        "weights": {
            "developer": {
                dimension: (1.0 / len(DIMENSIONS))
                for dimension in DIMENSIONS
            }
        },
        "scoring_method": "topsis",
    }

    conflicts_base = {
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": DEFAULT_STAKEHOLDERS,
        "ai_system": {
            "id": "invalid_conflicts",
            "name": "Invalid Conflicts",
            "description": "Mutation",
            "context": {"dimension_scores": evaluate_base["ai_system"]["context"]["dimension_scores"]},
        },
    }

    pareto_base = {
        "ai_system": {
            "id": "invalid_pareto",
            "name": "Invalid Pareto",
            "description": "Mutation",
            "context": {"dimension_scores": evaluate_base["ai_system"]["context"]["dimension_scores"]},
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": DEFAULT_STAKEHOLDERS,
        "n_solutions": 8,
        "pop_size": 32,
        "n_gen": 40,
        "seed": 42,
        "deterministic_mode": True,
    }

    mutation_cases = [
        (
            "/api/evaluate",
            evaluate_base,
            lambda payload: payload["ai_system"]["context"]["dimension_scores"].pop("accountability"),
        ),
        (
            "/api/conflicts",
            conflicts_base,
            lambda payload: payload.pop("ai_system"),
        ),
        (
            "/api/pareto",
            pareto_base,
            lambda payload: payload.update({"stakeholder_ids": ["developer"]}),
        ),
    ]

    with TestClient(app) as client:
        for endpoint, base_payload, mutate in mutation_cases:
            invalid_payload_first = deepcopy(base_payload)
            invalid_payload_second = deepcopy(base_payload)
            mutate(invalid_payload_first)
            mutate(invalid_payload_second)

            first = client.post(endpoint, json=invalid_payload_first)
            second = client.post(endpoint, json=invalid_payload_second)

            assert first.status_code == 422
            assert second.status_code == 422

            first_body = first.json()
            second_body = second.json()
            assert _detail_shape(first_body) == _detail_shape(second_body)
