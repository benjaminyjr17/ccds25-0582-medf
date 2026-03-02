from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from app.main import app

# Generated from current frozen OpenAPI schema using canonical JSON serialization.
EXPECTED_OPENAPI_SHA256 = "54631dca5d38c4b14afa197e50691a4734848917d3898ac4d2d39a4ecef1d3bc"

EXPECTED_POST_ENDPOINTS = {
    "/api/evaluate",
    "/api/conflicts",
    "/api/pareto",
}

EXPECTED_GET_ENDPOINTS = {
    "/api/frameworks",
    "/api/frameworks/{framework_id}",
    "/api/stakeholders",
    "/api/health",
}

# Full frozen /api surface (including legacy POST /api/stakeholders).
EXPECTED_API_SURFACE = {
    "/api/conflicts": {"post"},
    "/api/evaluate": {"post"},
    "/api/frameworks": {"get"},
    "/api/frameworks/{framework_id}": {"get"},
    "/api/health": {"get"},
    "/api/pareto": {"post"},
    "/api/stakeholders": {"get", "post"},
}


def _get_openapi() -> dict:
    with TestClient(app) as client:
        response = client.get("/api/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def test_api_surface_is_frozen() -> None:
    payload = _get_openapi()
    paths = payload.get("paths", {})

    api_surface = {
        path: {method.lower() for method in methods.keys()}
        for path, methods in paths.items()
        if path.startswith("/api/") and isinstance(methods, dict)
    }

    actual_post_endpoints = {
        path
        for path, methods in api_surface.items()
        if "post" in methods and path != "/api/stakeholders"
    }
    actual_get_endpoints = {
        path
        for path, methods in api_surface.items()
        if "get" in methods
    }

    assert actual_post_endpoints == EXPECTED_POST_ENDPOINTS, "API surface changed — feature freeze violated."
    assert actual_get_endpoints == EXPECTED_GET_ENDPOINTS, "API surface changed — feature freeze violated."
    assert api_surface == EXPECTED_API_SURFACE, "API surface changed — feature freeze violated."


def test_openapi_schema_fingerprint_is_frozen() -> None:
    payload = _get_openapi()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    current_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert current_hash == EXPECTED_OPENAPI_SHA256, "OpenAPI schema changed — feature freeze violated."
