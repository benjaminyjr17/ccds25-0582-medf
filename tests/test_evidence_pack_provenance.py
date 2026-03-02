from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "docs" / "evidence" / "evaluation_bundle.json"


def test_evidence_bundle_contains_case_provenance() -> None:
    assert BUNDLE.exists(), f"Missing evidence bundle: {BUNDLE}"
    with BUNDLE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert isinstance(payload, dict), "evaluation_bundle.json must be an object."
    rows = payload.get("rows")
    assert isinstance(rows, list) and rows, "evaluation_bundle.json rows must be a non-empty list."

    for row in rows:
        assert isinstance(row, dict), "Each evidence row must be an object."
        provenance = row.get("provenance")
        assert isinstance(provenance, dict), "Each evidence row must include provenance."
        deployment_type = str(provenance.get("deployment_type", "")).strip()
        assert deployment_type == "real_deployment", (
            f"Expected deployment_type='real_deployment', got '{deployment_type}'."
        )
        source_ids = provenance.get("source_ids")
        assert isinstance(source_ids, list), "provenance.source_ids must be a list."
        cleaned = [str(item).strip() for item in source_ids if str(item).strip()]
        assert len(cleaned) >= 3, "Each evidence row must include at least 3 source ids."
