from __future__ import annotations

import math

from fastapi.testclient import TestClient

from app.main import app
from app.models import UNIFIED_DIMENSIONS


def test_health_endpoint_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "healthy"
    assert payload["version"] == "1.0.0"
    assert isinstance(payload["frameworks_loaded"], int)
    assert isinstance(payload["stakeholder_profiles_loaded"], int)
    assert payload["frameworks_loaded"] >= 3
    assert payload["stakeholder_profiles_loaded"] >= 3


def test_frameworks_list_and_item_endpoints() -> None:
    with TestClient(app) as client:
        list_response = client.get("/api/frameworks")
        assert list_response.status_code == 200
        frameworks = list_response.json()

        assert isinstance(frameworks, list)
        assert len(frameworks) >= 3

        for framework in frameworks:
            assert isinstance(framework["id"], str)
            assert "dimensions" in framework
            dimensions = framework["dimensions"]
            assert isinstance(dimensions, list)
            assert len(dimensions) == 6

            dimension_ids = {item["id"] for item in dimensions}
            assert dimension_ids == set(UNIFIED_DIMENSIONS)

        framework_id = frameworks[0]["id"]
        item_response = client.get(f"/api/frameworks/{framework_id}")
        assert item_response.status_code == 200
        item = item_response.json()
        assert item["id"] == framework_id
        assert len(item["dimensions"]) == 6

        not_found_response = client.get("/api/frameworks/does_not_exist")
        assert not_found_response.status_code == 404


def test_stakeholders_endpoint_shape_and_weights() -> None:
    with TestClient(app) as client:
        response = client.get("/api/stakeholders")

    assert response.status_code == 200
    stakeholders = response.json()

    assert isinstance(stakeholders, list)
    assert len(stakeholders) >= 3

    stakeholder_ids = {item["id"] for item in stakeholders}
    assert {"developer", "regulator", "affected_community"}.issubset(stakeholder_ids)

    valid_roles = {"developer", "regulator", "affected_community", "custom"}
    expected_dimensions = set(UNIFIED_DIMENSIONS)

    for stakeholder in stakeholders:
        assert isinstance(stakeholder["id"], str)
        assert isinstance(stakeholder["name"], str)
        assert stakeholder["role"] in valid_roles
        assert "weights" in stakeholder

        weights = stakeholder["weights"]
        assert isinstance(weights, dict)
        assert set(weights.keys()) == expected_dimensions

        weight_sum = sum(float(value) for value in weights.values())
        assert math.isclose(weight_sum, 1.0, abs_tol=0.01)
