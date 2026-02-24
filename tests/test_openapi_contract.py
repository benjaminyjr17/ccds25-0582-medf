from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_includes_critical_paths() -> None:
    with TestClient(app) as client:
        response = client.get("/api/openapi.json")

    assert response.status_code == 200
    body = response.json()
    paths = body.get("paths", {})

    assert "/api/evaluate" in paths
    assert "/api/conflicts" in paths
    assert "/api/pareto" in paths
    assert "/api/frameworks" in paths
    assert "/api/stakeholders" in paths
