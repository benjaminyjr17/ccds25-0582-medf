from __future__ import annotations

from fastapi.testclient import TestClient

from app.framework_registry import get_framework, load_frameworks
from app.main import app
from app.models import UNIFIED_DIMENSIONS
from app.routers.evaluate import _framework_section_weights, router as evaluate_router


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


def _l1_distance(vector_a: tuple[float, ...], vector_b: tuple[float, ...]) -> float:
    return float(sum(abs(a - b) for a, b in zip(vector_a, vector_b)))


def _framework_prior_vector(framework_id: str) -> tuple[float, ...]:
    framework = get_framework(framework_id)
    assert framework is not None, f"Framework '{framework_id}' not found."
    weights = _framework_section_weights(framework)
    return tuple(float(weights[dimension]) for dimension in UNIFIED_DIMENSIONS)


def test_framework_section_weight_vectors_are_not_identical() -> None:
    load_frameworks()

    required_framework_ids = ["eu_altai", "nist_ai_rmf", "sg_mgaf"]
    vectors = {
        framework_id: _framework_prior_vector(framework_id)
        for framework_id in required_framework_ids
    }
    rounded_vectors = {
        framework_id: tuple(round(value, 6) for value in vector)
        for framework_id, vector in vectors.items()
    }
    print("section_priors:", rounded_vectors)

    for framework_id, vector in vectors.items():
        assert abs(sum(vector) - 1.0) <= 1e-6, (
            f"Section prior for {framework_id} does not sum to 1.0: {vector}"
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

    max_distance = max(pairwise_l1.values())
    assert max_distance > 0.05, (
        "Framework section-based priors identical; YAML lacks section mapping coverage. "
        f"vectors={rounded_vectors}, pairwise_l1={pairwise_l1}"
    )


def test_evaluate_scores_differ_for_most_different_frameworks() -> None:
    if not any(route.path == "/api/evaluate" for route in app.routes):
        app.include_router(evaluate_router)

    load_frameworks()
    framework_ids = ["eu_altai", "nist_ai_rmf", "sg_mgaf"]
    prior_vectors = {
        framework_id: _framework_prior_vector(framework_id)
        for framework_id in framework_ids
    }
    rounded_vectors = {
        framework_id: tuple(round(value, 6) for value in vector)
        for framework_id, vector in prior_vectors.items()
    }

    max_pair: tuple[str, str] | None = None
    max_distance = -1.0
    for index, left_id in enumerate(framework_ids):
        for right_id in framework_ids[index + 1:]:
            distance = _l1_distance(prior_vectors[left_id], prior_vectors[right_id])
            if distance > max_distance:
                max_distance = distance
                max_pair = (left_id, right_id)

    assert max_pair is not None

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
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
        "weights": {
            "developer": {
                "transparency_explainability": 0.10,
                "fairness_nondiscrimination": 0.15,
                "safety_robustness": 0.30,
                "privacy_data_governance": 0.15,
                "human_agency_oversight": 0.15,
                "accountability": 0.15,
            },
            "regulator": {
                "transparency_explainability": 0.20,
                "fairness_nondiscrimination": 0.20,
                "safety_robustness": 0.10,
                "privacy_data_governance": 0.15,
                "human_agency_oversight": 0.10,
                "accountability": 0.25,
            },
            "affected_community": {
                "transparency_explainability": 0.10,
                "fairness_nondiscrimination": 0.30,
                "safety_robustness": 0.10,
                "privacy_data_governance": 0.15,
                "human_agency_oversight": 0.20,
                "accountability": 0.15,
            }
        },
        "scoring_method": "topsis",
    }

    with TestClient(app) as client:
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
        "Framework section-based priors did not change evaluate score. "
        f"framework_pair={max_pair}, "
        f"wf_left={rounded_vectors[max_pair[0]]}, "
        f"wf_right={rounded_vectors[max_pair[1]]}, "
        f"scores=({score_one}, {score_two}), "
        f"l1_distance={max_distance}"
    )
