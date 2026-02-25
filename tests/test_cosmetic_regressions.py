from __future__ import annotations

import json
import re
from typing import Any

from fastapi.testclient import TestClient

from app.main import app

_UNDEFINED_TOKEN = re.compile(r"(^|\W)undefined(\W|$)")


def contains_literal_undefined(obj: Any) -> bool:
    if isinstance(obj, str):
        if obj == "undefined":
            return True
        return _UNDEFINED_TOKEN.search(obj) is not None

    if isinstance(obj, dict):
        return any(contains_literal_undefined(value) for value in obj.values())

    if isinstance(obj, (list, tuple)):
        return any(contains_literal_undefined(item) for item in obj)

    return False


def _pretty_snippet(payload: Any, limit: int = 2000) -> str:
    try:
        text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    except Exception:
        text = str(payload)
    if len(text) > limit:
        return text[:limit] + "\n...<truncated>..."
    return text


def _assert_endpoint_has_no_undefined(
    client: TestClient,
    *,
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if method == "GET":
        response = client.get(endpoint)
    elif method == "POST":
        response = client.post(endpoint, json=payload)
    else:
        raise AssertionError(f"Unsupported method for test: {method}")

    try:
        body = response.json()
    except Exception:
        body = {"raw_text": response.text}

    assert response.status_code == 200, (
        f"{method} {endpoint} returned status={response.status_code}, expected 200.\n"
        f"Response:\n{_pretty_snippet(body)}"
    )

    assert not contains_literal_undefined(body), (
        f"{method} {endpoint} emitted literal 'undefined'. status={response.status_code}\n"
        f"Response:\n{_pretty_snippet(body)}"
    )


def test_api_responses_never_emit_literal_undefined() -> None:
    evaluate_payload = {
        "ai_system": {
            "id": "facial_rec_system",
            "name": "Facial Recognition",
            "description": "Cosmetic regression test system",
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

    conflicts_payload = {
        "ai_system": {
            "id": "facial_rec_system",
            "name": "Facial Recognition",
            "description": "Cosmetic regression test system",
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
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
    }

    pareto_payload = {
        "ai_system": {
            "id": "facerec_1",
            "name": "FaceDetect Pro v2.1",
            "description": "Cosmetic regression test system",
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
        "stakeholder_ids": ["developer", "regulator", "affected_community"],
        "n_solutions": 8,
        "pop_size": 32,
        "n_gen": 40,
        "seed": 7,
        "deterministic_mode": True,
    }

    with TestClient(app) as client:
        _assert_endpoint_has_no_undefined(client, method="GET", endpoint="/api/health")
        _assert_endpoint_has_no_undefined(client, method="GET", endpoint="/api/frameworks")
        _assert_endpoint_has_no_undefined(client, method="GET", endpoint="/api/stakeholders")
        _assert_endpoint_has_no_undefined(
            client,
            method="POST",
            endpoint="/api/evaluate",
            payload=evaluate_payload,
        )
        _assert_endpoint_has_no_undefined(
            client,
            method="POST",
            endpoint="/api/conflicts",
            payload=conflicts_payload,
        )
        _assert_endpoint_has_no_undefined(
            client,
            method="POST",
            endpoint="/api/pareto",
            payload=pareto_payload,
        )
