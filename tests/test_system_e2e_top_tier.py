from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.framework_registry import get_framework, load_frameworks
from app.main import app
from app.models import UNIFIED_DIMENSIONS
from app.routers.evaluate import _framework_section_weights


DIMENSIONS = list(UNIFIED_DIMENSIONS)
EPS = 1e-9

S_BASE = {
    "transparency_explainability": 2.5,
    "fairness_nondiscrimination": 1.0,
    "safety_robustness": 5.5,
    "privacy_data_governance": 1.0,
    "human_agency_oversight": 2.5,
    "accountability": 4.0,
}
S_ALL_EQUAL = {dimension: 4.0 for dimension in DIMENSIONS}
S_ONE_DOMINANT = {
    "transparency_explainability": 1.0,
    "fairness_nondiscrimination": 1.0,
    "safety_robustness": 7.0,
    "privacy_data_governance": 1.0,
    "human_agency_oversight": 1.0,
    "accountability": 1.0,
}
S_ZERO_VECTOR = {dimension: 0.0 for dimension in DIMENSIONS}
S_BOUNDARY = {
    "transparency_explainability": 1.0,
    "fairness_nondiscrimination": 7.0,
    "safety_robustness": 1.0,
    "privacy_data_governance": 7.0,
    "human_agency_oversight": 1.0,
    "accountability": 7.0,
}

W_UNIFORM = {dimension: 1.0 / len(DIMENSIONS) for dimension in DIMENSIONS}
W_SAFETY_HEAVY = {
    "transparency_explainability": 0.1,
    "fairness_nondiscrimination": 0.1,
    "safety_robustness": 0.5,
    "privacy_data_governance": 0.1,
    "human_agency_oversight": 0.1,
    "accountability": 0.1,
}
W_TRANSP_HEAVY = {
    "transparency_explainability": 0.5,
    "fairness_nondiscrimination": 0.1,
    "safety_robustness": 0.1,
    "privacy_data_governance": 0.1,
    "human_agency_oversight": 0.1,
    "accountability": 0.1,
}
W_SINGLE_DIM = {
    "transparency_explainability": 0.0,
    "fairness_nondiscrimination": 0.0,
    "safety_robustness": 1.0,
    "privacy_data_governance": 0.0,
    "human_agency_oversight": 0.0,
    "accountability": 0.0,
}
W_INVALID_NEG = {
    "transparency_explainability": -0.1,
    "fairness_nondiscrimination": 0.2,
    "safety_robustness": 0.2,
    "privacy_data_governance": 0.2,
    "human_agency_oversight": 0.2,
    "accountability": 0.3,
}
W_INVALID_SUM = {
    "transparency_explainability": 0.30,
    "fairness_nondiscrimination": 0.30,
    "safety_robustness": 0.30,
    "privacy_data_governance": 0.10,
    "human_agency_oversight": 0.10,
    "accountability": 0.10,
}
W_INVALID_NAN = {
    "transparency_explainability": float("nan"),
    "fairness_nondiscrimination": 0.2,
    "safety_robustness": 0.2,
    "privacy_data_governance": 0.2,
    "human_agency_oversight": 0.2,
    "accountability": 0.2,
}

STAKEHOLDERS = ["developer", "regulator", "affected_community"]


def _pretty(data: Any) -> str:
    try:
        return json.dumps(data, indent=2, sort_keys=True, default=str)
    except Exception:
        return repr(data)


def assert_finite(value: float, *, label: str) -> None:
    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
        f"{label} must be numeric, got {type(value)} with value={value!r}."
    )
    assert math.isfinite(float(value)), f"{label} must be finite, got {value!r}."


def assert_in_01(value: float, *, label: str, eps: float = EPS) -> None:
    assert_finite(value, label=label)
    numeric = float(value)
    assert -eps <= numeric <= 1.0 + eps, (
        f"{label} must be in [0,1] within eps={eps}; got {numeric}."
    )


def _json_or_fail(response, *, label: str) -> Any:
    assert response.status_code != 500, (
        f"Internal error for {label}. status=500 body={response.text}"
    )
    try:
        return response.json()
    except Exception as exc:
        raise AssertionError(
            f"{label} returned non-JSON response. status={response.status_code} body={response.text}"
        ) from exc


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _dfs_find_first_numeric_named(payload: Any, target_key: str) -> float | None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key == target_key and _is_numeric(value):
                return float(value)
            nested = _dfs_find_first_numeric_named(value, target_key)
            if nested is not None:
                return nested
        return None
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for item in payload:
            nested = _dfs_find_first_numeric_named(item, target_key)
            if nested is not None:
                return nested
    return None


def _extract_overall_score(response_json: Any) -> float:
    if isinstance(response_json, Mapping):
        results = response_json.get("results")
        if isinstance(results, list) and results and isinstance(results[0], Mapping):
            value = results[0].get("overall_score")
            if _is_numeric(value):
                return float(value)

        direct = response_json.get("overall_score")
        if _is_numeric(direct):
            return float(direct)

    found = _dfs_find_first_numeric_named(response_json, "overall_score")
    if found is not None:
        return found

    raise AssertionError(
        "Unable to extract overall_score from /api/evaluate response. "
        f"Response snippet:\n{_pretty(response_json)[:2500]}"
    )


def _extract_stakeholder_overall(response_json: Any, stakeholder_id: str) -> float:
    if isinstance(response_json, Mapping):
        results = response_json.get("results")
        if isinstance(results, list) and results and isinstance(results[0], Mapping):
            stakeholder_scores = results[0].get("stakeholder_scores")
            if isinstance(stakeholder_scores, Mapping):
                entry = stakeholder_scores.get(stakeholder_id)
                if isinstance(entry, Mapping) and _is_numeric(entry.get("overall_score")):
                    return float(entry["overall_score"])

    stack = [response_json]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if stakeholder_id in current and isinstance(current[stakeholder_id], Mapping):
                nested = current[stakeholder_id]
                value = nested.get("overall_score")
                if _is_numeric(value):
                    return float(value)
            if current.get("stakeholder_id") == stakeholder_id and _is_numeric(current.get("overall_score")):
                return float(current["overall_score"])
            stack.extend(current.values())
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(current)

    raise AssertionError(
        f"Unable to extract stakeholder overall_score for '{stakeholder_id}'. "
        f"Response snippet:\n{_pretty(response_json)[:2500]}"
    )


def _extract_dimension_scores(response_json: Any) -> dict[str, float]:
    candidate_maps: list[dict[str, Any]] = []

    if isinstance(response_json, Mapping):
        results = response_json.get("results")
        if isinstance(results, list) and results and isinstance(results[0], Mapping):
            value = results[0].get("dimension_scores")
            if isinstance(value, Mapping):
                candidate_maps.append(dict(value))

        framework_scores = response_json.get("framework_scores")
        if isinstance(framework_scores, list) and framework_scores and isinstance(framework_scores[0], Mapping):
            value = framework_scores[0].get("dimension_scores")
            if isinstance(value, Mapping):
                candidate_maps.append(dict(value))

        direct = response_json.get("dimension_scores")
        if isinstance(direct, Mapping):
            candidate_maps.append(dict(direct))

    for candidate in candidate_maps:
        converted: dict[str, float] = {}
        for dim, value in candidate.items():
            if dim in DIMENSIONS and _is_numeric(value):
                converted[dim] = float(value)
        if converted:
            return converted

    stack = [response_json]
    while stack:
        current = stack.pop()
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            if all(
                isinstance(item, Mapping)
                and isinstance(item.get("dimension"), str)
                and _is_numeric(item.get("score"))
                for item in current
            ):
                converted = {
                    str(item["dimension"]): float(item["score"])
                    for item in current
                    if str(item["dimension"]) in DIMENSIONS
                }
                if converted:
                    return converted
            stack.extend(current)
        elif isinstance(current, Mapping):
            stack.extend(current.values())

    raise AssertionError(
        "Unable to extract dimension scores from /api/evaluate response. "
        f"Response snippet:\n{_pretty(response_json)[:2500]}"
    )


def _default_weights_from_stakeholders(client: TestClient, stakeholder_ids: list[str]) -> dict[str, dict[str, float]]:
    response = client.get("/api/stakeholders")
    payload = _json_or_fail(response, label="GET /api/stakeholders")
    assert response.status_code == 200, (
        f"/api/stakeholders failed. status={response.status_code} body={_pretty(payload)}"
    )
    assert isinstance(payload, list), f"/api/stakeholders payload is not list: {type(payload)}"
    by_id = {
        str(item.get("id")): item
        for item in payload
        if isinstance(item, Mapping)
    }

    out: dict[str, dict[str, float]] = {}
    for stakeholder_id in stakeholder_ids:
        assert stakeholder_id in by_id, (
            f"Missing stakeholder '{stakeholder_id}' in /api/stakeholders payload: {list(by_id)}"
        )
        raw_weights = by_id[stakeholder_id].get("weights")
        assert isinstance(raw_weights, Mapping), (
            f"Stakeholder '{stakeholder_id}' has invalid weights object: {raw_weights!r}"
        )
        out[stakeholder_id] = {dim: float(raw_weights[dim]) for dim in DIMENSIONS}
    return out


def _get_frameworks(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/api/frameworks")
    payload = _json_or_fail(response, label="GET /api/frameworks")
    assert response.status_code == 200, (
        f"/api/frameworks failed. status={response.status_code} body={_pretty(payload)}"
    )
    assert isinstance(payload, list) and payload, (
        f"/api/frameworks returned empty/invalid payload: {_pretty(payload)}"
    )
    return [item for item in payload if isinstance(item, Mapping)]


def _framework_prior_vector(framework_id: str) -> tuple[float, ...]:
    load_frameworks()
    framework = get_framework(framework_id)
    assert framework is not None, f"Framework '{framework_id}' not found in registry."
    weights = _framework_section_weights(framework)
    return tuple(float(weights[dimension]) for dimension in DIMENSIONS)


def _max_distance_framework_pair(framework_ids: list[str]) -> tuple[tuple[str, str], float, dict[str, tuple[float, ...]]]:
    prior_vectors = {framework_id: _framework_prior_vector(framework_id) for framework_id in framework_ids}
    max_pair: tuple[str, str] | None = None
    max_distance = -1.0
    for i, left in enumerate(framework_ids):
        for right in framework_ids[i + 1 :]:
            dist = float(sum(abs(a - b) for a, b in zip(prior_vectors[left], prior_vectors[right])))
            if dist > max_distance:
                max_distance = dist
                max_pair = (left, right)
    assert max_pair is not None, f"No framework pair available from ids={framework_ids}"
    return max_pair, max_distance, prior_vectors


def _evaluate_payload(
    *,
    framework_ids: list[str],
    stakeholder_ids: list[str],
    weights: dict[str, dict[str, float]],
    score_map: dict[str, float],
    scoring_method: str,
) -> dict[str, Any]:
    return {
        "ai_system": {
            "id": "e2e_system",
            "name": "E2E System",
            "description": "Top-tier E2E test payload",
            "context": {"dimension_scores": score_map},
        },
        "framework_ids": framework_ids,
        "stakeholder_ids": stakeholder_ids,
        "weights": weights,
        "scoring_method": scoring_method,
    }


def _post_json_allow_nan(client: TestClient, path: str, payload: dict[str, Any]):
    content = json.dumps(payload, allow_nan=True)
    response = client.post(path, content=content, headers={"Content-Type": "application/json"})
    return response


def _extract_conflict_matrix(response_json: Any, *, key: str) -> dict[str, dict[str, float]]:
    if isinstance(response_json, Mapping):
        metadata = response_json.get("metadata")
        if isinstance(metadata, Mapping):
            matrix = metadata.get(key)
            if isinstance(matrix, Mapping):
                out: dict[str, dict[str, float]] = {}
                for row_key, row_value in matrix.items():
                    if isinstance(row_value, Mapping):
                        out[str(row_key)] = {
                            str(col_key): float(col_value)
                            for col_key, col_value in row_value.items()
                            if _is_numeric(col_value)
                        }
                if out:
                    return out
    raise AssertionError(
        f"Unable to extract conflict matrix '{key}'. Response snippet:\n{_pretty(response_json)[:2500]}"
    )


def _extract_pareto_solutions(response_json: Any) -> list[dict[str, Any]]:
    if isinstance(response_json, Mapping):
        for key in ("pareto_solutions", "frontier", "solutions"):
            value = response_json.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
    raise AssertionError(
        "Unable to extract Pareto solutions list. "
        f"Response snippet:\n{_pretty(response_json)[:2500]}"
    )


def _dominates_minimize(a: dict[str, float], b: dict[str, float], *, eps: float = 1e-12) -> bool:
    all_le = all(a[key] <= b[key] + eps for key in a)
    any_lt = any(a[key] < b[key] - eps for key in a)
    return all_le and any_lt


def test_evaluate_smoke_topsis_and_wsm_contract() -> None:
    with TestClient(app) as client:
        frameworks = _get_frameworks(client)
        framework_id = str(frameworks[0]["id"])
        default_weights = _default_weights_from_stakeholders(client, ["developer"])

        # Validate criteria_type handling for whatever the framework declares.
        criteria_types = [
            str(dimension.get("criteria_type", "")).strip().lower()
            for dimension in frameworks[0].get("dimensions", [])
            if isinstance(dimension, Mapping)
        ]
        assert criteria_types, f"No criteria_type values found in framework payload: {_pretty(frameworks[0])}"
        invalid_types = [value for value in criteria_types if value not in {"benefit", "cost"}]
        assert not invalid_types, (
            f"Invalid criteria_type values found: {invalid_types}. framework={framework_id}"
        )

        topsis_payload = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights=default_weights,
            score_map=S_BASE,
            scoring_method="topsis",
        )
        topsis_response = client.post("/api/evaluate", json=topsis_payload)
        topsis_body = _json_or_fail(topsis_response, label="POST /api/evaluate topsis")
        assert topsis_response.status_code == 200, (
            f"TOPSIS evaluate failed. status={topsis_response.status_code} body={_pretty(topsis_body)}"
        )

        topsis_overall = _extract_overall_score(topsis_body)
        assert_finite(topsis_overall, label="topsis_overall_score")
        assert_in_01(topsis_overall, label="topsis_overall_score")

        try:
            dev_overall = _extract_stakeholder_overall(topsis_body, "developer")
        except AssertionError:
            # Single-stakeholder requests can safely use overall as stakeholder proxy.
            dev_overall = topsis_overall
        assert_finite(dev_overall, label="developer_overall_score")
        assert_in_01(dev_overall, label="developer_overall_score")

        topsis_dims = _extract_dimension_scores(topsis_body)
        assert set(topsis_dims) == set(DIMENSIONS), (
            f"TOPSIS dimension scores missing keys. got={sorted(topsis_dims)} expected={sorted(DIMENSIONS)} "
            f"body={_pretty(topsis_body)}"
        )
        for dim, value in topsis_dims.items():
            assert_finite(value, label=f"topsis_dimension_score[{dim}]")
            assert_in_01(value, label=f"topsis_dimension_score[{dim}]")

        wsm_payload = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights=default_weights,
            score_map=S_BASE,
            scoring_method="wsm",
        )
        wsm_response = client.post("/api/evaluate", json=wsm_payload)
        wsm_body = _json_or_fail(wsm_response, label="POST /api/evaluate wsm")
        if wsm_response.status_code in {400, 422}:
            pytest.skip(f"WSM not supported by current backend contract: {_pretty(wsm_body)}")
        assert wsm_response.status_code == 200, (
            f"WSM evaluate failed. status={wsm_response.status_code} body={_pretty(wsm_body)}"
        )
        wsm_overall = _extract_overall_score(wsm_body)
        assert_finite(wsm_overall, label="wsm_overall_score")
        assert_in_01(wsm_overall, label="wsm_overall_score")


def test_weight_override_changes_outputs_monotonicity() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])

        payload_safety = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_SAFETY_HEAVY},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        payload_transparency = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_TRANSP_HEAVY},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        response_safety = client.post("/api/evaluate", json=payload_safety)
        body_safety = _json_or_fail(response_safety, label="evaluate safety-heavy")
        response_transparency = client.post("/api/evaluate", json=payload_transparency)
        body_transparency = _json_or_fail(response_transparency, label="evaluate transparency-heavy")

        assert response_safety.status_code == 200, (
            f"Safety-heavy override failed. status={response_safety.status_code} body={_pretty(body_safety)}"
        )
        assert response_transparency.status_code == 200, (
            f"Transparency-heavy override failed. status={response_transparency.status_code} body={_pretty(body_transparency)}"
        )

        score_safety = _extract_overall_score(body_safety)
        score_transparency = _extract_overall_score(body_transparency)
        assert abs(score_safety - score_transparency) > 1e-9, (
            "Changing stakeholder override weights did not change score. "
            f"safety_score={score_safety}, transparency_score={score_transparency}, "
            f"safety_body={_pretty(body_safety)}, transparency_body={_pretty(body_transparency)}"
        )

        payload_single = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_SINGLE_DIM},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        response_single = client.post("/api/evaluate", json=payload_single)
        body_single = _json_or_fail(response_single, label="evaluate single-dim")
        assert response_single.status_code == 200, (
            f"Single-dimension override failed. status={response_single.status_code} body={_pretty(body_single)}"
        )

        contributions = _extract_dimension_scores(body_single)
        top_dim = max(contributions, key=contributions.get)
        assert top_dim == "safety_robustness", (
            "Single-dimension override should force top contribution on safety_robustness. "
            f"top_dim={top_dim}, contributions={contributions}, weights={W_SINGLE_DIM}"
        )


def test_invalid_weights_rejected() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])

        negative_payload = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_INVALID_NEG},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        negative_response = client.post("/api/evaluate", json=negative_payload)
        negative_body = _json_or_fail(negative_response, label="evaluate invalid negative weights")
        assert negative_response.status_code in {400, 422}, (
            f"Negative weights must be rejected. status={negative_response.status_code} body={_pretty(negative_body)}"
        )

        invalid_sum_payload = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_INVALID_SUM},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        invalid_sum_response = client.post("/api/evaluate", json=invalid_sum_payload)
        invalid_sum_body = _json_or_fail(invalid_sum_response, label="evaluate invalid sum weights")
        if invalid_sum_response.status_code in {400, 422}:
            pass
        elif invalid_sum_response.status_code == 200:
            overall = _extract_overall_score(invalid_sum_body)
            assert_finite(overall, label="invalid_sum_overall_if_accepted")
            assert_in_01(overall, label="invalid_sum_overall_if_accepted")
        else:
            raise AssertionError(
                f"Unexpected status for invalid-sum weights. status={invalid_sum_response.status_code} "
                f"body={_pretty(invalid_sum_body)}"
            )

        nan_payload = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_INVALID_NAN},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        nan_response = _post_json_allow_nan(client, "/api/evaluate", nan_payload)
        nan_body = _json_or_fail(nan_response, label="evaluate NaN weights")
        assert nan_response.status_code in {400, 422}, (
            f"NaN weights must be rejected. status={nan_response.status_code} body={_pretty(nan_body)}"
        )


def test_invalid_dimension_scores_rejected_or_handled() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])
        default_weights = _default_weights_from_stakeholders(client, ["developer"])

        for label, score_map in (
            ("zero_vector", S_ZERO_VECTOR),
            ("out_of_range", {**S_BASE, "safety_robustness": 8.0}),
            ("boundary", S_BOUNDARY),
        ):
            payload = _evaluate_payload(
                framework_ids=[framework_id],
                stakeholder_ids=["developer"],
                weights=default_weights,
                score_map=score_map,
                scoring_method="topsis",
            )
            response = client.post("/api/evaluate", json=payload)
            body = _json_or_fail(response, label=f"evaluate {label}")
            assert response.status_code != 500, (
                f"Internal error on {label} dimension scores. body={_pretty(body)}"
            )
            if response.status_code in {400, 422}:
                continue
            if response.status_code == 200:
                overall = _extract_overall_score(body)
                assert_finite(overall, label=f"{label}_overall")
                dims = _extract_dimension_scores(body)
                for dim, value in dims.items():
                    assert_finite(value, label=f"{label}_dimension[{dim}]")
                continue
            raise AssertionError(
                f"Unexpected status for {label} dimension scores. status={response.status_code} body={_pretty(body)}"
            )


def test_framework_switch_changes_score_or_explains_identical_priors() -> None:
    with TestClient(app) as client:
        frameworks = _get_frameworks(client)
        framework_ids = [str(item["id"]) for item in frameworks if "id" in item]
        if len(framework_ids) < 2:
            pytest.skip("Need >=2 frameworks for switching test.")

        pair, max_dist, prior_vectors = _max_distance_framework_pair(framework_ids)

        payload_common = _evaluate_payload(
            framework_ids=[],
            stakeholder_ids=STAKEHOLDERS,
            weights={
                "developer": W_SAFETY_HEAVY,
                "regulator": W_UNIFORM,
                "affected_community": W_UNIFORM,
            },
            score_map=S_BASE,
            scoring_method="topsis",
        )

        payload_one = dict(payload_common)
        payload_one["framework_ids"] = [pair[0]]
        payload_two = dict(payload_common)
        payload_two["framework_ids"] = [pair[1]]

        response_one = client.post("/api/evaluate", json=payload_one)
        body_one = _json_or_fail(response_one, label="framework switch first")
        response_two = client.post("/api/evaluate", json=payload_two)
        body_two = _json_or_fail(response_two, label="framework switch second")
        assert response_one.status_code == 200, (
            f"First framework evaluate failed. status={response_one.status_code} body={_pretty(body_one)}"
        )
        assert response_two.status_code == 200, (
            f"Second framework evaluate failed. status={response_two.status_code} body={_pretty(body_two)}"
        )

        score_one = _extract_overall_score(body_one)
        score_two = _extract_overall_score(body_two)
        if abs(score_one - score_two) <= 1e-9:
            raise AssertionError(
                "Framework switch produced identical overall_score. This indicates either identical "
                "framework priors/mappings OR framework not applied in evaluate. Check framework-weight "
                "derivation and YAML mappings. "
                f"framework_pair={pair}, max_l1={max_dist}, "
                f"priors={ {k: tuple(round(v, 6) for v in vals) for k, vals in prior_vectors.items()} }, "
                f"scores=({score_one}, {score_two})"
            )


def test_topsis_single_alternative_not_constant_bug() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])

        payload_base = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_SAFETY_HEAVY},
            score_map=S_BASE,
            scoring_method="topsis",
        )
        payload_dominant = _evaluate_payload(
            framework_ids=[framework_id],
            stakeholder_ids=["developer"],
            weights={"developer": W_SAFETY_HEAVY},
            score_map=S_ONE_DOMINANT,
            scoring_method="topsis",
        )

        response_base = client.post("/api/evaluate", json=payload_base)
        body_base = _json_or_fail(response_base, label="topsis base")
        response_dom = client.post("/api/evaluate", json=payload_dominant)
        body_dom = _json_or_fail(response_dom, label="topsis one_dominant")
        assert response_base.status_code == 200, (
            f"TOPSIS baseline failed. status={response_base.status_code} body={_pretty(body_base)}"
        )
        assert response_dom.status_code == 200, (
            f"TOPSIS one-dominant failed. status={response_dom.status_code} body={_pretty(body_dom)}"
        )

        score_base = _extract_overall_score(body_base)
        score_dom = _extract_overall_score(body_dom)
        assert abs(score_base - score_dom) > 1e-9, (
            "TOPSIS output invariant to input; likely single-alternative TOPSIS "
            "degeneracy/constant score bug. "
            f"score_base={score_base}, score_one_dominant={score_dom}, "
            f"body_base={_pretty(body_base)}, body_dom={_pretty(body_dom)}"
        )


def test_conflicts_weights_only_vs_contribution_based_differ_when_system_salience_changes() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])

        def run_conflicts(score_map: dict[str, float]) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[str, Any]]:
            payload = {
                "framework_ids": [framework_id],
                "stakeholder_ids": STAKEHOLDERS,
                "ai_system": {
                    "id": "conflict_test",
                    "name": "Conflict Test",
                    "description": "E2E conflict test",
                    "context": {"dimension_scores": score_map},
                },
            }
            response = client.post("/api/conflicts", json=payload)
            body = _json_or_fail(response, label="POST /api/conflicts")
            assert response.status_code == 200, (
                f"/api/conflicts failed. status={response.status_code} body={_pretty(body)}"
            )
            weights_matrix = _extract_conflict_matrix(body, key="correlation_matrix_weights")
            contrib_matrix = _extract_conflict_matrix(body, key="correlation_matrix_contrib")
            return weights_matrix, contrib_matrix, body

        weights_a, contrib_a, body_a = run_conflicts(S_BASE)
        weights_b, contrib_b, body_b = run_conflicts(S_ONE_DOMINANT)

        # Weights-only must be input-score invariant when stakeholder weights are unchanged.
        for row in STAKEHOLDERS:
            for col in STAKEHOLDERS:
                a = float(weights_a.get(row, {}).get(col, 0.0))
                b = float(weights_b.get(row, {}).get(col, 0.0))
                assert abs(a - b) <= 1e-9, (
                    "weights-only conflict matrix changed across systems with same stakeholder weights. "
                    f"pair=({row},{col}) base={a} dominant={b} "
                    f"base_body={_pretty(body_a)} dominant_body={_pretty(body_b)}"
                )

        # Contribution-based should react to changed system salience.
        changed_pairs = []
        for row in STAKEHOLDERS:
            for col in STAKEHOLDERS:
                a = float(contrib_a.get(row, {}).get(col, 0.0))
                b = float(contrib_b.get(row, {}).get(col, 0.0))
                if abs(a - b) > 1e-6:
                    changed_pairs.append((row, col, a, b))
        assert changed_pairs, (
            "contribution-based conflict matrix did not change when system salience changed. "
            f"contrib_base={contrib_a} contrib_dominant={contrib_b}"
        )


def test_pareto_frontier_basic_properties() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])
        payload = {
            "ai_system": {
                "id": "pareto_test",
                "name": "Pareto Test",
                "description": "E2E pareto test",
                "context": {"dimension_scores": S_BASE},
            },
            "framework_ids": [framework_id],
            "stakeholder_ids": STAKEHOLDERS,
            "n_solutions": 8,
            "pop_size": 32,
            "n_gen": 40,
            "seed": 13,
            "deterministic_mode": True,
        }

        response = client.post("/api/pareto", json=payload)
        body = _json_or_fail(response, label="POST /api/pareto")
        assert response.status_code == 200, (
            f"/api/pareto failed. status={response.status_code} body={_pretty(body)}"
        )

        solutions = _extract_pareto_solutions(body)
        if len(solutions) < 2:
            pytest.skip(f"Pareto returned <2 solutions; cannot evaluate dominance. body={_pretty(body)}")

        objective_vectors: list[dict[str, float]] = []
        for index, solution in enumerate(solutions):
            objective_scores = solution.get("objective_scores")
            assert isinstance(objective_scores, Mapping), (
                f"Pareto solution #{index} missing objective_scores. solution={_pretty(solution)}"
            )
            vector = {}
            for stakeholder_id in STAKEHOLDERS:
                value = objective_scores.get(stakeholder_id)
                assert _is_numeric(value), (
                    f"Pareto solution #{index} objective for '{stakeholder_id}' invalid: {value!r}. "
                    f"solution={_pretty(solution)}"
                )
                vector[stakeholder_id] = float(value)
            objective_vectors.append(vector)

            consensus = solution.get("weights", {}).get("consensus")
            assert isinstance(consensus, Mapping), (
                f"Pareto solution #{index} missing consensus weights. solution={_pretty(solution)}"
            )
            consensus_sum = float(sum(float(consensus.get(dim, 0.0)) for dim in DIMENSIONS))
            assert abs(consensus_sum - 1.0) <= 0.01, (
                f"Pareto consensus weights do not sum to 1. solution={_pretty(solution)}"
            )

        for i, vec_i in enumerate(objective_vectors):
            for j, vec_j in enumerate(objective_vectors):
                if i == j:
                    continue
                assert not _dominates_minimize(vec_j, vec_i), (
                    "Returned Pareto set contains dominated point. "
                    f"solution_{j} dominates solution_{i}. "
                    f"dominator={vec_j}, dominated={vec_i}, body={_pretty(body)}"
                )


def test_pareto_respects_weight_changes_directionally() -> None:
    with TestClient(app) as client:
        framework_id = str(_get_frameworks(client)[0]["id"])
        stakeholder_ids = ["developer", "regulator"]

        def run(weights: dict[str, dict[str, float]]) -> dict[str, Any]:
            payload = {
                "ai_system": {
                    "id": "pareto_directional",
                    "name": "Pareto Directional",
                    "description": "Directional sanity test",
                    "context": {"dimension_scores": S_BASE},
                },
                "framework_ids": [framework_id],
                "stakeholder_ids": stakeholder_ids,
                "weights": weights,
                "n_solutions": 8,
                "pop_size": 32,
                "n_gen": 40,
                "seed": 7,
                "deterministic_mode": True,
            }
            response = client.post("/api/pareto", json=payload)
            body = _json_or_fail(response, label="POST /api/pareto directional")
            assert response.status_code == 200, (
                f"Directional pareto call failed. status={response.status_code} body={_pretty(body)}"
            )
            solutions = _extract_pareto_solutions(body)
            assert solutions, f"Pareto returned no solutions. body={_pretty(body)}"
            ranked = sorted(
                solutions,
                key=lambda item: int(item.get("rank", 10**9)),
            )
            return dict(ranked[0])

        top_safety = run(
            {
                "developer": W_SAFETY_HEAVY,
                "regulator": W_SAFETY_HEAVY,
            }
        )
        top_transparency = run(
            {
                "developer": W_TRANSP_HEAVY,
                "regulator": W_TRANSP_HEAVY,
            }
        )

        consensus_safety = top_safety.get("weights", {}).get("consensus", {})
        consensus_transparency = top_transparency.get("weights", {}).get("consensus", {})
        assert isinstance(consensus_safety, Mapping) and isinstance(consensus_transparency, Mapping), (
            "Unable to extract top-solution consensus weights for directional Pareto test. "
            f"top_safety={_pretty(top_safety)} top_transparency={_pretty(top_transparency)}"
        )

        safety_in_safety_run = float(consensus_safety.get("safety_robustness", 0.0))
        safety_in_trans_run = float(consensus_transparency.get("safety_robustness", 0.0))
        transp_in_safety_run = float(consensus_safety.get("transparency_explainability", 0.0))
        transp_in_trans_run = float(consensus_transparency.get("transparency_explainability", 0.0))

        assert safety_in_safety_run > safety_in_trans_run + 1e-6, (
            "Pareto solutions did not shift toward safety when safety-heavy preferences were supplied. "
            f"safety_run={safety_in_safety_run}, trans_run={safety_in_trans_run}, "
            f"top_safety={_pretty(top_safety)}, top_transparency={_pretty(top_transparency)}"
        )
        assert transp_in_trans_run > transp_in_safety_run + 1e-6, (
            "Pareto solutions did not shift toward transparency when transparency-heavy preferences were supplied. "
            f"trans_run={transp_in_trans_run}, safety_run={transp_in_safety_run}, "
            f"top_safety={_pretty(top_safety)}, top_transparency={_pretty(top_transparency)}"
        )
