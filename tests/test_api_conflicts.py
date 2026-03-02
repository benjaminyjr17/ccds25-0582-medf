from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import UNIFIED_DIMENSIONS
from app.routers.conflicts import router as conflicts_router


def test_conflicts_endpoint_returns_pairwise_spearman_results() -> None:
    if not any(route.path == "/api/conflicts" for route in app.routes):
        app.include_router(conflicts_router)

    payload = {
        "ai_system": {
            "id": "facial_rec_system",
            "name": "Facial Recognition",
            "description": "Stage 2 conflicts integration test system",
            "context": {
                "dimension_scores": {
                    "transparency_explainability": 2.5,
                    "fairness_nondiscrimination": 1,
                    "safety_robustness": 5.5,
                    "privacy_data_governance": 1,
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

    assert response.status_code == 200
    body = response.json()

    assert isinstance(body.get("conflicts"), list)
    assert len(body["conflicts"]) == 3

    allowed_levels = {"low", "moderate", "high"}
    for item in body["conflicts"]:
        assert -1.0 <= float(item["spearman_rho"]) <= 1.0
        assert item["conflict_level"] in allowed_levels

    metadata = body.get("metadata", {})
    assert "correlation_matrix" in metadata
    assert "stakeholder_rankings" in metadata
    assert "correlation_matrix_weights" in metadata
    assert "stakeholder_rankings_weights" in metadata

    harm_assessment = body.get("harm_assessment")
    assert isinstance(harm_assessment, dict)
    assert harm_assessment.get("model_version") == "harm_taxonomy_v1"
    overall_score = float(harm_assessment.get("overall_score", -1.0))
    assert 0.0 <= overall_score <= 1.0
    assert harm_assessment.get("overall_severity") in {"low", "moderate", "high", "critical"}

    domain_scores = harm_assessment.get("domain_scores")
    assert isinstance(domain_scores, list)
    assert len(domain_scores) == len(UNIFIED_DIMENSIONS)
    seen_dimensions: set[str] = set()
    for item in domain_scores:
        assert isinstance(item, dict)
        unified_dimension = str(item.get("unified_dimension", ""))
        seen_dimensions.add(unified_dimension)
        assert unified_dimension in UNIFIED_DIMENSIONS
        score = float(item.get("score", -1.0))
        assert 0.0 <= score <= 1.0
        assert item.get("severity") in {"low", "moderate", "high", "critical"}
    assert seen_dimensions == set(UNIFIED_DIMENSIONS)

    top_risk_domains = harm_assessment.get("top_risk_domains")
    assert isinstance(top_risk_domains, list)
    assert top_risk_domains
    assert set(top_risk_domains).issubset(set(UNIFIED_DIMENSIONS))

    stakeholder_ids = payload["stakeholder_ids"]
    expected_dimensions = set(UNIFIED_DIMENSIONS)

    for matrix_key in ("correlation_matrix", "correlation_matrix_weights"):
        matrix = metadata.get(matrix_key)
        assert isinstance(matrix, dict)
        for stakeholder_a in stakeholder_ids:
            assert stakeholder_a in matrix
            row = matrix[stakeholder_a]
            assert isinstance(row, dict)
            assert stakeholder_a in row
            assert abs(float(row[stakeholder_a]) - 1.0) <= 1e-6
            for stakeholder_b in stakeholder_ids:
                assert stakeholder_b in row
                ab = float(matrix[stakeholder_a][stakeholder_b])
                ba = float(matrix[stakeholder_b][stakeholder_a])
                assert abs(ab - ba) <= 1e-6

    rankings_weights = metadata.get("stakeholder_rankings_weights")
    assert isinstance(rankings_weights, dict)
    for stakeholder_id in stakeholder_ids:
        assert stakeholder_id in rankings_weights
        ranking = rankings_weights[stakeholder_id]
        assert isinstance(ranking, list)
        assert len(ranking) == len(UNIFIED_DIMENSIONS)
        assert set(ranking) == expected_dimensions

    weights_matrix = metadata.get("correlation_matrix_weights")
    if not isinstance(weights_matrix, dict):
        pytest.skip("Missing correlation_matrix_weights in metadata.")
    try:
        dev_reg = float(weights_matrix["developer"]["regulator"])
        dev_aff = float(weights_matrix["developer"]["affected_community"])
    except KeyError:
        pytest.skip(
            "Missing required stakeholder ids in correlation_matrix_weights "
            "(developer, regulator, affected_community)."
        )
    assert dev_aff <= dev_reg
