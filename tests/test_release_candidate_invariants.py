from __future__ import annotations

import json
import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.models import UNIFIED_DIMENSIONS

DIMENSIONS = list(UNIFIED_DIMENSIONS)
RNG = random.Random(1337)


def _snippet(data: Any, limit: int = 2000) -> str:
    try:
        rendered = json.dumps(data, sort_keys=True, default=str)
    except Exception:
        rendered = repr(data)
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit] + "..."


def walk_has_nan_inf(obj: Any) -> bool:
    if isinstance(obj, bool) or obj is None:
        return False
    if isinstance(obj, float):
        return math.isnan(obj) or math.isinf(obj)
    if isinstance(obj, int):
        return False
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if walk_has_nan_inf(key) or walk_has_nan_inf(value):
                return True
        return False
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        for item in obj:
            if walk_has_nan_inf(item):
                return True
        return False
    return False


def assert_json_no_nan_inf(json_obj: Any, context: str) -> None:
    assert not walk_has_nan_inf(json_obj), (
        f"{context}: JSON contains NaN/inf. response_snippet={_snippet(json_obj)}"
    )


def assert_weights_sum_to_one(weights: dict[str, float], tol: float = 1e-6) -> None:
    total = 0.0
    for dimension, raw_value in weights.items():
        value = float(raw_value)
        assert math.isfinite(value), f"Non-finite weight for '{dimension}': {raw_value!r}"
        assert value >= 0.0, f"Negative weight for '{dimension}': {value}"
        total += value

    assert abs(total - 1.0) <= tol, (
        f"Weight sum must be 1.0 within tol={tol}. got={total:.12f} weights={weights}"
    )


def assert_rho_bounds(conflict_json: Any, context: str) -> None:
    found_rho = False

    def _walk(node: Any, *, rho_context: bool = False, path: str = "root") -> None:
        nonlocal found_rho

        if isinstance(node, Mapping):
            for key, value in node.items():
                key_text = str(key).lower()
                next_rho_context = rho_context or ("rho" in key_text)
                _walk(value, rho_context=next_rho_context, path=f"{path}.{key}")
            return

        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for idx, item in enumerate(node):
                _walk(item, rho_context=rho_context, path=f"{path}[{idx}]")
            return

        if rho_context and isinstance(node, (int, float)) and not isinstance(node, bool):
            found_rho = True
            value = float(node)
            assert math.isfinite(value), f"{context}: non-finite rho at {path} value={node!r}"
            assert -1.0 - 1e-12 <= value <= 1.0 + 1e-12, (
                f"{context}: rho out of bounds at {path} value={value} "
                f"response_snippet={_snippet(conflict_json)}"
            )

    _walk(conflict_json)
    assert found_rho, (
        f"{context}: no rho values found in conflicts response. "
        f"response_snippet={_snippet(conflict_json)}"
    )


def assert_score_bounds(eval_json: Any, context: str) -> None:
    tolerance = 1e-9

    overall_scores: list[float] = []
    dimension_maps: list[dict[str, Any]] = []

    stack = [eval_json]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            for key, value in current.items():
                if key == "overall_score" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    overall_scores.append(float(value))
                if key == "dimension_scores" and isinstance(value, Mapping):
                    dimension_maps.append(dict(value))
                if isinstance(value, (Mapping, list, tuple)):
                    stack.append(value)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(current)

    assert overall_scores, (
        f"{context}: could not find overall_score in evaluate response. "
        f"response_snippet={_snippet(eval_json)}"
    )
    for overall in overall_scores:
        assert math.isfinite(overall), (
            f"{context}: overall_score is not finite ({overall}). "
            f"response_snippet={_snippet(eval_json)}"
        )

    assert dimension_maps, (
        f"{context}: could not find dimension_scores map in evaluate response. "
        f"response_snippet={_snippet(eval_json)}"
    )

    checked_dimension_values = 0
    for dim_map in dimension_maps:
        for dimension, raw_value in dim_map.items():
            if dimension not in DIMENSIONS:
                continue
            value = float(raw_value)
            checked_dimension_values += 1
            assert math.isfinite(value), (
                f"{context}: dimension score is non-finite for '{dimension}'. "
                f"value={raw_value!r} response_snippet={_snippet(eval_json)}"
            )
            assert -tolerance <= value <= 1.0 + tolerance, (
                f"{context}: dimension score out of [0,1] for '{dimension}'. "
                f"value={value} response_snippet={_snippet(eval_json)}"
            )

    assert checked_dimension_values > 0, (
        f"{context}: no normalized dimension scores were validated. "
        f"response_snippet={_snippet(eval_json)}"
    )


def _dominates_minimize(
    point_a: dict[str, float],
    point_b: dict[str, float],
    keys: list[str],
    *,
    eps: float = 1e-12,
) -> bool:
    all_le = all(point_a[key] <= point_b[key] + eps for key in keys)
    any_lt = any(point_a[key] < point_b[key] - eps for key in keys)
    return all_le and any_lt


def pareto_is_nondominated(points: list[dict], keys: list[str]) -> bool:
    if len(points) <= 1:
        return True

    numeric_points: list[dict[str, float]] = []
    for point in points:
        numeric_point: dict[str, float] = {}
        for key in keys:
            if key not in point:
                return False
            value = float(point[key])
            if not math.isfinite(value):
                return False
            numeric_point[key] = value
        numeric_points.append(numeric_point)

    for idx_a, point_a in enumerate(numeric_points):
        for idx_b, point_b in enumerate(numeric_points):
            if idx_a == idx_b:
                continue
            if _dominates_minimize(point_b, point_a, keys):
                return False

    return True


def assert_harm_assessment_bounds(conflict_json: Any, context: str) -> None:
    assert isinstance(conflict_json, Mapping), (
        f"{context}: expected object payload. response_snippet={_snippet(conflict_json)}"
    )
    harm_assessment = conflict_json.get("harm_assessment")
    assert isinstance(harm_assessment, Mapping), (
        f"{context}: missing harm_assessment payload. response_snippet={_snippet(conflict_json)}"
    )
    overall = float(harm_assessment.get("overall_score", -1.0))
    assert math.isfinite(overall) and 0.0 <= overall <= 1.0, (
        f"{context}: invalid harm overall_score={overall}. "
        f"response_snippet={_snippet(conflict_json)}"
    )
    domain_scores = harm_assessment.get("domain_scores")
    assert isinstance(domain_scores, list) and domain_scores, (
        f"{context}: harm domain_scores missing. response_snippet={_snippet(conflict_json)}"
    )
    seen: set[str] = set()
    for item in domain_scores:
        assert isinstance(item, Mapping), (
            f"{context}: invalid harm domain entry. response_snippet={_snippet(conflict_json)}"
        )
        dimension = str(item.get("unified_dimension", ""))
        seen.add(dimension)
        assert dimension in DIMENSIONS, (
            f"{context}: unknown harm dimension '{dimension}'. "
            f"response_snippet={_snippet(conflict_json)}"
        )
        score = float(item.get("score", -1.0))
        assert math.isfinite(score) and 0.0 <= score <= 1.0, (
            f"{context}: harm score out of bounds for '{dimension}' value={score}. "
            f"response_snippet={_snippet(conflict_json)}"
        )
    assert seen == set(DIMENSIONS), (
        f"{context}: harm dimensions incomplete. seen={sorted(seen)} expected={sorted(DIMENSIONS)}"
    )


def test_release_candidate_base_endpoints_have_valid_json() -> None:
    endpoints = ["/api/frameworks", "/api/stakeholders", "/api/health"]
    RNG.shuffle(endpoints)

    with TestClient(app) as client:
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, (
                f"endpoint={endpoint} expected=200 got={response.status_code} body={response.text}"
            )
            payload = response.json()
            assert_json_no_nan_inf(payload, context=f"endpoint={endpoint}")

            if endpoint == "/api/frameworks":
                assert isinstance(payload, list) and len(payload) >= 1, (
                    f"endpoint={endpoint} expected non-empty list. payload={_snippet(payload)}"
                )

            if endpoint == "/api/stakeholders":
                assert isinstance(payload, list) and len(payload) >= 1, (
                    f"endpoint={endpoint} expected non-empty list. payload={_snippet(payload)}"
                )
                ids = {
                    str(item.get("id"))
                    for item in payload
                    if isinstance(item, Mapping) and item.get("id") is not None
                }
                expected = {"developer", "regulator", "affected_community"}
                assert expected.issubset(ids) or len(ids) > 0, (
                    f"endpoint={endpoint} expected default stakeholders or non-empty ids. "
                    f"ids={sorted(ids)} payload={_snippet(payload)}"
                )


def test_release_candidate_conflicts_endpoint_harm_payload_is_valid() -> None:
    payload = {
        "ai_system": {
            "id": "release_candidate_conflicts_harm",
            "name": "Release Candidate Conflicts Harm",
            "description": "Invariant validation for harm output payload",
            "context": {
                "dimension_scores": {
                    "transparency_explainability": 2.5,
                    "fairness_nondiscrimination": 1.0,
                    "safety_robustness": 5.5,
                    "privacy_data_governance": 1.0,
                    "human_agency_oversight": 2.5,
                    "accountability": 4.0,
                }
            },
        },
        "framework_ids": ["eu_altai"],
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
    }

    with TestClient(app) as client:
        response = client.post("/api/conflicts", json=payload)

    assert response.status_code == 200, (
        f"endpoint=/api/conflicts expected=200 got={response.status_code} body={response.text}"
    )
    conflict_json = response.json()
    assert_json_no_nan_inf(conflict_json, context="endpoint=/api/conflicts")
    assert_rho_bounds(conflict_json, context="endpoint=/api/conflicts")
    assert_harm_assessment_bounds(
        conflict_json,
        context="endpoint=/api/conflicts",
    )
