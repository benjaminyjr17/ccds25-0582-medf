from __future__ import annotations

from collections.abc import Mapping

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


def _coverage_count(dimension_payload: Mapping[str, object]) -> float:
    assessment_questions = dimension_payload.get("assessment_questions")
    if isinstance(assessment_questions, list):
        non_empty = [
            str(question).strip()
            for question in assessment_questions
            if str(question).strip()
        ]
        if non_empty:
            return float(len(non_empty))

    for key in ("criteria", "subcriteria", "items"):
        values = dimension_payload.get(key)
        if isinstance(values, list) and len(values) > 0:
            return float(len(values))

    return 1.0


def _framework_prior_vector(framework_payload: Mapping[str, object]) -> tuple[float, ...]:
    dimensions = framework_payload.get("dimensions")
    assert isinstance(dimensions, list)

    by_name: dict[str, Mapping[str, object]] = {}
    for item in dimensions:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        if isinstance(name, str):
            by_name[name] = item

    missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in by_name]
    assert not missing, f"Framework payload missing canonical dimensions: {missing}"

    raw = [_coverage_count(by_name[dimension]) for dimension in UNIFIED_DIMENSIONS]
    total = float(sum(raw))
    assert abs(total) > 0.0, "Framework prior normalization sum is zero."
    return tuple(value / total for value in raw)


def _l1_distance(vector_a: tuple[float, ...], vector_b: tuple[float, ...]) -> float:
    return float(sum(abs(a - b) for a, b in zip(vector_a, vector_b)))


def test_framework_coverage_prior_vectors_are_differentiated() -> None:
    if not any(route.path == "/api/evaluate" for route in app.routes):
        app.include_router(evaluate_router)

    with TestClient(app) as client:
        frameworks_response = client.get("/api/frameworks")
        assert frameworks_response.status_code == 200
        frameworks = frameworks_response.json()
        assert isinstance(frameworks, list)

    frameworks_by_id = {
        str(framework.get("id")): framework
        for framework in frameworks
        if isinstance(framework, dict)
    }

    required_framework_ids = ["eu_altai", "nist_ai_rmf", "sg_mgaf"]
    missing_frameworks = [
        framework_id for framework_id in required_framework_ids if framework_id not in frameworks_by_id
    ]
    assert not missing_frameworks, f"Missing frameworks for coverage-prior test: {missing_frameworks}"

    vectors = {
        framework_id: _framework_prior_vector(frameworks_by_id[framework_id])
        for framework_id in required_framework_ids
    }

    for framework_id, vector in vectors.items():
        assert abs(sum(vector) - 1.0) <= 1e-6, (
            f"Coverage prior for {framework_id} does not sum to 1.0: {vector}"
        )

    pairs = [
        ("eu_altai", "nist_ai_rmf"),
        ("eu_altai", "sg_mgaf"),
        ("nist_ai_rmf", "sg_mgaf"),
    ]
    pairwise_l1 = {
        f"{left}|{right}": _l1_distance(vectors[left], vectors[right])
        for left, right in pairs
    }

    assert any(distance > 1e-6 for distance in pairwise_l1.values()), (
        "Framework YAML encodes identical coverage counts per dimension; "
        "cannot differentiate frameworks without enriching YAML mappings. "
        f"vectors={vectors}, pairwise_l1={pairwise_l1}"
    )


def test_evaluate_scores_differ_across_frameworks_with_coverage_priors() -> None:
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
        framework_ids = [framework["id"] for framework in frameworks if isinstance(framework, dict) and "id" in framework]
        assert len(framework_ids) >= 2

        prior_vectors = {
            framework["id"]: _framework_prior_vector(framework)
            for framework in frameworks
            if isinstance(framework, dict) and isinstance(framework.get("id"), str)
        }
        assert len(prior_vectors) >= 2

        max_pair: tuple[str, str] | None = None
        max_distance = -1.0
        ids = list(prior_vectors.keys())
        for index, left_id in enumerate(ids):
            for right_id in ids[index + 1:]:
                distance = _l1_distance(prior_vectors[left_id], prior_vectors[right_id])
                if distance > max_distance:
                    max_distance = distance
                    max_pair = (left_id, right_id)

        assert max_pair is not None

        payload_one = dict(base_payload)
        payload_one["framework_ids"] = [max_pair[0]]
        response_one = client.post("/api/evaluate", json=payload_one)
        assert response_one.status_code == 200
        score_one = float(response_one.json()["overall_score"])

        payload_two = dict(base_payload)
        payload_two["framework_ids"] = [max_pair[1]]
        response_two = client.post("/api/evaluate", json=payload_two)
        assert response_two.status_code == 200
        score_two = float(response_two.json()["overall_score"])

    assert abs(score_one - score_two) > 1e-9, (
        "Framework-aware coverage weighting did not change score. "
        f"framework_pair={max_pair}, "
        f"wf_left={prior_vectors[max_pair[0]]}, "
        f"wf_right={prior_vectors[max_pair[1]]}, "
        f"scores=({score_one}, {score_two}), "
        f"l1_distance={max_distance}"
    )
