from __future__ import annotations

import json
import math
import random
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS
from app.routers.pareto import ParetoRequest
from tests.test_release_candidate_invariants import (
    assert_json_no_nan_inf,
    assert_rho_bounds,
    assert_score_bounds,
    assert_weights_sum_to_one,
    pareto_is_nondominated,
)

DIMENSIONS = list(UNIFIED_DIMENSIONS)
STAKEHOLDERS = ["developer", "regulator", "affected_community"]

# Reused preset vectors from existing top-tier E2E tests.
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


def _snippet(data: Any, limit: int = 1600) -> str:
    try:
        rendered = json.dumps(data, sort_keys=True, default=str)
    except Exception:
        rendered = repr(data)
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit] + "..."


def _json_or_text(response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"non_json_body": response.text}


def _get_framework_ids(client: TestClient) -> list[str]:
    response = client.get("/api/frameworks")
    payload = _json_or_text(response)
    assert response.status_code == 200, (
        f"endpoint=/api/frameworks expected=200 got={response.status_code} body={_snippet(payload)}"
    )
    assert isinstance(payload, list) and payload, (
        f"endpoint=/api/frameworks expected non-empty list. body={_snippet(payload)}"
    )

    framework_ids = [
        str(item["id"])
        for item in payload
        if isinstance(item, Mapping) and item.get("id")
    ]
    assert framework_ids, f"No framework ids found in payload={_snippet(payload)}"
    return framework_ids


def _default_weights_from_stakeholders(
    client: TestClient,
    stakeholder_ids: list[str],
) -> dict[str, dict[str, float]]:
    response = client.get("/api/stakeholders")
    payload = _json_or_text(response)
    assert response.status_code == 200, (
        f"endpoint=/api/stakeholders expected=200 got={response.status_code} body={_snippet(payload)}"
    )
    assert isinstance(payload, list), (
        f"endpoint=/api/stakeholders expected list payload. body={_snippet(payload)}"
    )

    by_id = {
        str(item.get("id")): item
        for item in payload
        if isinstance(item, Mapping)
    }

    weights: dict[str, dict[str, float]] = {}
    for stakeholder_id in stakeholder_ids:
        assert stakeholder_id in by_id, (
            f"Missing stakeholder '{stakeholder_id}' in /api/stakeholders payload ids={sorted(by_id)}"
        )
        raw_weights = by_id[stakeholder_id].get("weights")
        assert isinstance(raw_weights, Mapping), (
            f"Stakeholder '{stakeholder_id}' has invalid weights map: {raw_weights!r}"
        )
        weights[stakeholder_id] = {
            dimension: float(raw_weights[dimension])
            for dimension in DIMENSIONS
        }

    return weights


def _evaluate_payload(
    *,
    framework_id: str,
    stakeholder_ids: list[str],
    weights: dict[str, dict[str, float]],
    score_map: dict[str, float],
) -> dict[str, Any]:
    return {
        "ai_system": {
            "id": "rc_stress_eval",
            "name": "RC Stress Evaluate",
            "description": "Release candidate stress payload",
            "context": {"dimension_scores": score_map},
        },
        "framework_ids": [framework_id],
        "stakeholder_ids": stakeholder_ids,
        "weights": weights,
        "scoring_method": "topsis",
    }


def _conflicts_payload(
    *,
    framework_id: str,
    stakeholder_ids: list[str],
    score_map: dict[str, float],
) -> dict[str, Any]:
    return {
        "framework_ids": [framework_id],
        "stakeholder_ids": stakeholder_ids,
        "ai_system": {
            "id": "rc_stress_conflicts",
            "name": "RC Stress Conflicts",
            "description": "Release candidate stress payload",
            "context": {"dimension_scores": score_map},
        },
    }


def _pareto_payload(
    *,
    framework_id: str,
    stakeholder_ids: list[str],
    score_map: dict[str, float],
    n_solutions: int,
    pop_size: int,
    n_gen: int,
    seed: int,
    weights: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ai_system": {
            "id": "rc_stress_pareto",
            "name": "RC Stress Pareto",
            "description": "Release candidate stress payload",
            "context": {"dimension_scores": score_map},
        },
        "framework_ids": [framework_id],
        "stakeholder_ids": stakeholder_ids,
        "n_solutions": n_solutions,
        "pop_size": pop_size,
        "n_gen": n_gen,
        "seed": seed,
        "deterministic_mode": True,
    }
    if weights is not None:
        payload["weights"] = weights
    return payload


def _extract_overall_score(response_json: Any) -> float:
    if isinstance(response_json, Mapping):
        direct = response_json.get("overall_score")
        if isinstance(direct, (int, float)) and not isinstance(direct, bool):
            return float(direct)

        framework_scores = response_json.get("framework_scores")
        if isinstance(framework_scores, list) and framework_scores:
            candidate = framework_scores[0].get("score") if isinstance(framework_scores[0], Mapping) else None
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return float(candidate)

    raise AssertionError(
        f"Unable to extract overall score from evaluate response: {_snippet(response_json)}"
    )


def _extract_dimension_scores(response_json: Any) -> dict[str, float]:
    if isinstance(response_json, Mapping):
        framework_scores = response_json.get("framework_scores")
        if isinstance(framework_scores, list):
            for item in framework_scores:
                if not isinstance(item, Mapping):
                    continue
                raw_map = item.get("dimension_scores")
                if isinstance(raw_map, Mapping):
                    extracted = {
                        dimension: float(raw_map[dimension])
                        for dimension in DIMENSIONS
                        if dimension in raw_map
                    }
                    if extracted:
                        return extracted

        direct = response_json.get("dimension_scores")
        if isinstance(direct, Mapping):
            extracted = {
                dimension: float(direct[dimension])
                for dimension in DIMENSIONS
                if dimension in direct
            }
            if extracted:
                return extracted

    raise AssertionError(
        f"Unable to extract dimension scores from evaluate response: {_snippet(response_json)}"
    )


def _extract_conflict_signature(conflict_json: Any) -> list[tuple[str, str, float, str]]:
    if not isinstance(conflict_json, Mapping):
        raise AssertionError(f"Invalid conflicts response payload: {_snippet(conflict_json)}")

    conflicts = conflict_json.get("conflicts")
    if not isinstance(conflicts, list):
        raise AssertionError(f"Missing conflicts list in payload: {_snippet(conflict_json)}")

    signature: list[tuple[str, str, float, str]] = []
    for item in conflicts:
        if not isinstance(item, Mapping):
            raise AssertionError(f"Invalid conflict entry: {_snippet(item)}")
        stakeholder_a = str(item.get("stakeholder_a_id", ""))
        stakeholder_b = str(item.get("stakeholder_b_id", ""))
        conflict_level = str(item.get("conflict_level", ""))
        rho_value = item.get("spearman_rho")
        if not isinstance(rho_value, (int, float)) or isinstance(rho_value, bool):
            raise AssertionError(f"Invalid spearman_rho value in conflict item: {_snippet(item)}")
        pair = tuple(sorted((stakeholder_a, stakeholder_b)))
        signature.append((pair[0], pair[1], float(rho_value), conflict_level))

    signature.sort(key=lambda row: (row[0], row[1]))
    return signature


def _extract_pareto_solutions(response_json: Any) -> list[dict[str, Any]]:
    if isinstance(response_json, Mapping):
        for key in ("pareto_solutions", "frontier", "solutions"):
            raw = response_json.get(key)
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, Mapping)]
    return []


def _pareto_bounds() -> dict[str, int]:
    schema = ParetoRequest.model_json_schema()
    properties = schema.get("properties", {})

    def _bound(field: str, key: str, fallback: int) -> int:
        raw = properties.get(field, {}).get(key)
        if raw is None:
            return fallback
        return int(raw)

    return {
        "n_solutions_min": _bound("n_solutions", "minimum", 1),
        "n_solutions_max": _bound("n_solutions", "maximum", 50),
        "pop_size_min": _bound("pop_size", "minimum", 16),
        "pop_size_max": _bound("pop_size", "maximum", 256),
        "n_gen_min": _bound("n_gen", "minimum", 10),
        "n_gen_max": _bound("n_gen", "maximum", 300),
    }


def _candidate_steps(scale_min: float, scale_max: float) -> list[float]:
    if float(scale_min).is_integer() and float(scale_max).is_integer():
        start = int(scale_min)
        end = int(scale_max)
        return [float(value) for value in range(start, end + 1)]

    steps: list[float] = []
    value = float(scale_min)
    while value <= float(scale_max) + 1e-12:
        steps.append(round(value, 6))
        value += 0.5
    return steps


def _edge_vectors(scale_min: float, scale_max: float) -> dict[str, dict[str, float]]:
    midpoint = (float(scale_min) + float(scale_max)) / 2.0
    alternating = {
        dimension: (float(scale_min) if idx % 2 == 0 else float(scale_max))
        for idx, dimension in enumerate(DIMENSIONS)
    }

    return {
        "all_min": {dimension: float(scale_min) for dimension in DIMENSIONS},
        "all_max": {dimension: float(scale_max) for dimension in DIMENSIONS},
        "alternating_min_max": alternating,
        "midpoint": {dimension: float(midpoint) for dimension in DIMENSIONS},
        "skewed_safety": {
            "transparency_explainability": float(scale_min),
            "fairness_nondiscrimination": float(scale_min),
            "safety_robustness": float(scale_max),
            "privacy_data_governance": float(midpoint),
            "human_agency_oversight": float(midpoint),
            "accountability": float(scale_max),
        },
    }


def _random_vectors(
    *,
    rng: random.Random,
    count: int,
    candidates: list[float],
) -> list[dict[str, float]]:
    vectors: list[dict[str, float]] = []
    for _ in range(count):
        vectors.append(
            {
                dimension: float(rng.choice(candidates))
                for dimension in DIMENSIONS
            }
        )
    return vectors


def test_release_candidate_maximum_stress_endpoints() -> None:
    rng = random.Random(1337)

    with TestClient(app) as client:
        framework_ids = _get_framework_ids(client)
        baseline_weights = _default_weights_from_stakeholders(client, STAKEHOLDERS)

        presets = {
            "baseline": {
                stakeholder_id: dict(weights)
                for stakeholder_id, weights in baseline_weights.items()
            },
            "safety_heavy": {
                stakeholder_id: dict(W_SAFETY_HEAVY)
                for stakeholder_id in STAKEHOLDERS
            },
            "flipped": {
                stakeholder_id: dict(W_TRANSP_HEAVY)
                for stakeholder_id in STAKEHOLDERS
            },
        }

        for preset_name, preset_weights in presets.items():
            for stakeholder_id in STAKEHOLDERS:
                assert stakeholder_id in preset_weights, (
                    f"Preset '{preset_name}' missing weights for stakeholder '{stakeholder_id}'."
                )
                assert_weights_sum_to_one(preset_weights[stakeholder_id], tol=1e-6)

        edge_vectors = _edge_vectors(LIKERT_MIN, LIKERT_MAX)
        random_pool = _random_vectors(
            rng=rng,
            count=30,
            candidates=_candidate_steps(LIKERT_MIN, LIKERT_MAX),
        )
        random_subset = random_pool[:10]

        bounds = _pareto_bounds()
        safe_n_solutions = bounds["n_solutions_max"]
        safe_pop_size = max(bounds["pop_size_min"], min(120, bounds["pop_size_max"]))
        safe_n_gen = max(bounds["n_gen_min"], min(200, bounds["n_gen_max"]))

        preset_n_solutions = max(bounds["n_solutions_min"], min(12, bounds["n_solutions_max"]))
        preset_pop_size = max(bounds["pop_size_min"], min(48, bounds["pop_size_max"]))
        preset_n_gen = max(bounds["n_gen_min"], min(60, bounds["n_gen_max"]))

        for framework_id in framework_ids:
            for vector_name, score_map in edge_vectors.items():
                for preset_name, preset_weights in presets.items():
                    evaluate_payload = _evaluate_payload(
                        framework_id=framework_id,
                        stakeholder_ids=STAKEHOLDERS,
                        weights=preset_weights,
                        score_map=score_map,
                    )
                    evaluate_response = client.post("/api/evaluate", json=evaluate_payload)
                    evaluate_json = _json_or_text(evaluate_response)
                    evaluate_context = (
                        "endpoint=/api/evaluate "
                        f"framework={framework_id} vector={vector_name} preset={preset_name}"
                    )
                    assert evaluate_response.status_code == 200, (
                        f"{evaluate_context} status={evaluate_response.status_code} "
                        f"payload_summary=stakeholders={STAKEHOLDERS} response_snippet={_snippet(evaluate_json)}"
                    )
                    assert_json_no_nan_inf(evaluate_json, context=evaluate_context)
                    assert_score_bounds(evaluate_json, context=evaluate_context)

                conflicts_payload = _conflicts_payload(
                    framework_id=framework_id,
                    stakeholder_ids=STAKEHOLDERS,
                    score_map=score_map,
                )
                conflicts_response = client.post("/api/conflicts", json=conflicts_payload)
                conflicts_json = _json_or_text(conflicts_response)
                conflicts_context = (
                    "endpoint=/api/conflicts "
                    f"framework={framework_id} vector={vector_name}"
                )
                assert conflicts_response.status_code == 200, (
                    f"{conflicts_context} status={conflicts_response.status_code} "
                    f"payload_summary=stakeholders={STAKEHOLDERS} response_snippet={_snippet(conflicts_json)}"
                )
                assert_json_no_nan_inf(conflicts_json, context=conflicts_context)
                assert_rho_bounds(conflicts_json, context=conflicts_context)

            for index, score_map in enumerate(random_subset):
                vector_name = f"random_{index:02d}"

                evaluate_payload = _evaluate_payload(
                    framework_id=framework_id,
                    stakeholder_ids=STAKEHOLDERS,
                    weights=presets["baseline"],
                    score_map=score_map,
                )
                evaluate_response = client.post("/api/evaluate", json=evaluate_payload)
                evaluate_json = _json_or_text(evaluate_response)
                evaluate_context = (
                    "endpoint=/api/evaluate "
                    f"framework={framework_id} vector={vector_name} preset=baseline"
                )
                assert evaluate_response.status_code == 200, (
                    f"{evaluate_context} status={evaluate_response.status_code} "
                    f"payload_summary=stakeholders={STAKEHOLDERS} response_snippet={_snippet(evaluate_json)}"
                )
                assert_json_no_nan_inf(evaluate_json, context=evaluate_context)
                assert_score_bounds(evaluate_json, context=evaluate_context)

                conflicts_payload = _conflicts_payload(
                    framework_id=framework_id,
                    stakeholder_ids=STAKEHOLDERS,
                    score_map=score_map,
                )
                conflicts_response = client.post("/api/conflicts", json=conflicts_payload)
                conflicts_json = _json_or_text(conflicts_response)
                conflicts_context = (
                    "endpoint=/api/conflicts "
                    f"framework={framework_id} vector={vector_name}"
                )
                assert conflicts_response.status_code == 200, (
                    f"{conflicts_context} status={conflicts_response.status_code} "
                    f"payload_summary=stakeholders={STAKEHOLDERS} response_snippet={_snippet(conflicts_json)}"
                )
                assert_json_no_nan_inf(conflicts_json, context=conflicts_context)
                assert_rho_bounds(conflicts_json, context=conflicts_context)

            pareto_payload = _pareto_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                score_map=edge_vectors["midpoint"],
                n_solutions=safe_n_solutions,
                pop_size=safe_pop_size,
                n_gen=safe_n_gen,
                seed=7,
            )
            pareto_response = client.post("/api/pareto", json=pareto_payload)
            pareto_json = _json_or_text(pareto_response)
            pareto_context = (
                "endpoint=/api/pareto "
                f"framework={framework_id} run=safe_high n_solutions={safe_n_solutions} "
                f"pop_size={safe_pop_size} n_gen={safe_n_gen}"
            )
            assert pareto_response.status_code == 200, (
                f"{pareto_context} status={pareto_response.status_code} "
                f"response_snippet={_snippet(pareto_json)}"
            )
            assert_json_no_nan_inf(pareto_json, context=pareto_context)

            pareto_solutions = _extract_pareto_solutions(pareto_json)
            assert pareto_solutions, (
                f"{pareto_context} expected non-empty pareto_solutions. "
                f"response_snippet={_snippet(pareto_json)}"
            )

            objective_points: list[dict[str, float]] = []
            for solution in pareto_solutions:
                raw_weights = solution.get("weights")
                assert isinstance(raw_weights, Mapping), (
                    f"{pareto_context} missing solution weights. solution={_snippet(solution)}"
                )
                consensus = raw_weights.get("consensus") if isinstance(raw_weights, Mapping) else None
                assert isinstance(consensus, Mapping), (
                    f"{pareto_context} missing consensus weights. solution={_snippet(solution)}"
                )
                assert_weights_sum_to_one(
                    {
                        dimension: float(consensus[dimension])
                        for dimension in DIMENSIONS
                        if dimension in consensus
                    },
                    tol=0.01,
                )

                objective_scores = solution.get("objective_scores")
                assert isinstance(objective_scores, Mapping), (
                    f"{pareto_context} missing objective_scores. solution={_snippet(solution)}"
                )

                point: dict[str, float] = {}
                for stakeholder_id in STAKEHOLDERS:
                    assert stakeholder_id in objective_scores, (
                        f"{pareto_context} objective_scores missing stakeholder '{stakeholder_id}'. "
                        f"solution={_snippet(solution)}"
                    )
                    value = float(objective_scores[stakeholder_id])
                    assert math.isfinite(value), (
                        f"{pareto_context} non-finite objective score for stakeholder '{stakeholder_id}'. "
                        f"solution={_snippet(solution)}"
                    )
                    point[stakeholder_id] = value
                objective_points.append(point)

            assert pareto_is_nondominated(objective_points, STAKEHOLDERS), (
                f"{pareto_context} returned dominated solutions under minimize-objective convention. "
                f"response_snippet={_snippet(pareto_json)}"
            )

            pareto_preset_payload = _pareto_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                score_map=edge_vectors["skewed_safety"],
                n_solutions=preset_n_solutions,
                pop_size=preset_pop_size,
                n_gen=preset_n_gen,
                seed=11,
                weights=presets["safety_heavy"],
            )
            pareto_preset_response = client.post("/api/pareto", json=pareto_preset_payload)
            pareto_preset_json = _json_or_text(pareto_preset_response)
            pareto_preset_context = (
                "endpoint=/api/pareto "
                f"framework={framework_id} run=preset_safety n_solutions={preset_n_solutions} "
                f"pop_size={preset_pop_size} n_gen={preset_n_gen}"
            )
            assert pareto_preset_response.status_code == 200, (
                f"{pareto_preset_context} status={pareto_preset_response.status_code} "
                f"response_snippet={_snippet(pareto_preset_json)}"
            )
            assert_json_no_nan_inf(pareto_preset_json, context=pareto_preset_context)

            extreme_payload = _pareto_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                score_map=edge_vectors["all_max"],
                n_solutions=safe_n_solutions,
                pop_size=250,
                n_gen=500,
                seed=19,
            )
            extreme_response = client.post("/api/pareto", json=extreme_payload)
            extreme_json = _json_or_text(extreme_response)
            extreme_context = (
                "endpoint=/api/pareto "
                f"framework={framework_id} run=extreme pop_size=250 n_gen=500"
            )
            if extreme_response.status_code == 200:
                assert_json_no_nan_inf(extreme_json, context=extreme_context)
            else:
                assert extreme_response.status_code == 422, (
                    f"{extreme_context} expected 200 or 422, got {extreme_response.status_code}. "
                    f"response_snippet={_snippet(extreme_json)}"
                )


def test_release_candidate_repeatability_subset() -> None:
    edge_vectors = _edge_vectors(LIKERT_MIN, LIKERT_MAX)
    subset_vectors = [
        ("all_min", edge_vectors["all_min"]),
        ("midpoint", edge_vectors["midpoint"]),
        ("skewed_safety", edge_vectors["skewed_safety"]),
    ]

    with TestClient(app) as client:
        framework_id = _get_framework_ids(client)[0]
        baseline_weights = _default_weights_from_stakeholders(client, STAKEHOLDERS)

        for vector_name, score_map in subset_vectors:
            evaluate_payload = _evaluate_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                weights=baseline_weights,
                score_map=score_map,
            )

            evaluate_first = client.post("/api/evaluate", json=evaluate_payload)
            evaluate_second = client.post("/api/evaluate", json=evaluate_payload)
            eval_first_json = _json_or_text(evaluate_first)
            eval_second_json = _json_or_text(evaluate_second)

            eval_context = (
                "endpoint=/api/evaluate "
                f"framework={framework_id} vector={vector_name} repeat_check=true"
            )
            assert evaluate_first.status_code == 200, (
                f"{eval_context} first_call status={evaluate_first.status_code} "
                f"response_snippet={_snippet(eval_first_json)}"
            )
            assert evaluate_second.status_code == 200, (
                f"{eval_context} second_call status={evaluate_second.status_code} "
                f"response_snippet={_snippet(eval_second_json)}"
            )
            assert_json_no_nan_inf(eval_first_json, context=f"{eval_context} first")
            assert_json_no_nan_inf(eval_second_json, context=f"{eval_context} second")
            assert_score_bounds(eval_first_json, context=f"{eval_context} first")
            assert_score_bounds(eval_second_json, context=f"{eval_context} second")

            overall_first = _extract_overall_score(eval_first_json)
            overall_second = _extract_overall_score(eval_second_json)
            assert math.isclose(overall_first, overall_second, abs_tol=1e-12), (
                f"{eval_context} overall_score mismatch. "
                f"first={overall_first} second={overall_second}"
            )

            dimensions_first = _extract_dimension_scores(eval_first_json)
            dimensions_second = _extract_dimension_scores(eval_second_json)
            for dimension in DIMENSIONS:
                assert dimension in dimensions_first and dimension in dimensions_second, (
                    f"{eval_context} missing dimension '{dimension}'. "
                    f"first={dimensions_first} second={dimensions_second}"
                )
                assert math.isclose(
                    dimensions_first[dimension],
                    dimensions_second[dimension],
                    abs_tol=1e-12,
                ), (
                    f"{eval_context} dimension mismatch for '{dimension}'. "
                    f"first={dimensions_first[dimension]} second={dimensions_second[dimension]}"
                )

            conflicts_payload = _conflicts_payload(
                framework_id=framework_id,
                stakeholder_ids=STAKEHOLDERS,
                score_map=score_map,
            )

            conflicts_first = client.post("/api/conflicts", json=conflicts_payload)
            conflicts_second = client.post("/api/conflicts", json=conflicts_payload)
            conflicts_first_json = _json_or_text(conflicts_first)
            conflicts_second_json = _json_or_text(conflicts_second)

            conflicts_context = (
                "endpoint=/api/conflicts "
                f"framework={framework_id} vector={vector_name} repeat_check=true"
            )
            assert conflicts_first.status_code == 200, (
                f"{conflicts_context} first_call status={conflicts_first.status_code} "
                f"response_snippet={_snippet(conflicts_first_json)}"
            )
            assert conflicts_second.status_code == 200, (
                f"{conflicts_context} second_call status={conflicts_second.status_code} "
                f"response_snippet={_snippet(conflicts_second_json)}"
            )
            assert_json_no_nan_inf(conflicts_first_json, context=f"{conflicts_context} first")
            assert_json_no_nan_inf(conflicts_second_json, context=f"{conflicts_context} second")
            assert_rho_bounds(conflicts_first_json, context=f"{conflicts_context} first")
            assert_rho_bounds(conflicts_second_json, context=f"{conflicts_context} second")

            signature_first = _extract_conflict_signature(conflicts_first_json)
            signature_second = _extract_conflict_signature(conflicts_second_json)
            assert len(signature_first) == len(signature_second), (
                f"{conflicts_context} conflict list length mismatch. "
                f"first={signature_first} second={signature_second}"
            )

            for left, right in zip(signature_first, signature_second):
                assert left[0] == right[0] and left[1] == right[1], (
                    f"{conflicts_context} stakeholder pair mismatch. first={left} second={right}"
                )
                assert left[3] == right[3], (
                    f"{conflicts_context} conflict_level mismatch for pair {(left[0], left[1])}. "
                    f"first={left[3]} second={right[3]}"
                )
                assert math.isclose(left[2], right[2], abs_tol=1e-12), (
                    f"{conflicts_context} rho mismatch for pair {(left[0], left[1])}. "
                    f"first={left[2]} second={right[2]}"
                )
