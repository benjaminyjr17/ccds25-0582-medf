from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS
from streamlit_app import CASE_STUDIES, CASE_STUDY_FILES


ROOT = Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict), f"{path} must contain a JSON object."
    return payload


def _assert_non_empty_assumptions(path: Path, assumptions: Any) -> None:
    assert isinstance(assumptions, list), f"{path} assumptions must be a list of strings."
    assert assumptions, f"{path} assumptions list must not be empty."
    assert all(
        isinstance(item, str) and item.strip() for item in assumptions
    ), f"{path} assumptions list entries must be non-empty strings."


def _assert_evidence_manifest(path: Path, evidence_manifest: Any) -> None:
    assert isinstance(evidence_manifest, dict), f"{path} evidence_manifest must be an object."
    assert str(evidence_manifest.get("manifest_version", "")).strip(), (
        f"{path} evidence_manifest.manifest_version must be non-empty."
    )
    deployment_type = str(evidence_manifest.get("deployment_type", "")).strip()
    assert deployment_type == "real_deployment", (
        f"{path} evidence_manifest.deployment_type must be 'real_deployment'."
    )

    sources = evidence_manifest.get("sources")
    assert isinstance(sources, list), f"{path} evidence_manifest.sources must be a list."
    assert len(sources) >= 3, f"{path} evidence_manifest.sources must include at least 3 entries."

    source_ids: set[str] = set()
    for source in sources:
        assert isinstance(source, dict), f"{path} source entry must be an object."
        for required in (
            "source_id",
            "title",
            "authors",
            "publisher",
            "publication_date",
            "url",
            "accessed_date",
            "document_type",
            "license_status",
            "quote_allowed",
        ):
            assert required in source, f"{path} source missing required field '{required}'."
        source_id = str(source.get("source_id", "")).strip()
        assert source_id, f"{path} source_id must be non-empty."
        assert source_id not in source_ids, f"{path} duplicate source_id '{source_id}'."
        source_ids.add(source_id)

        url = str(source.get("url", "")).strip()
        assert url.startswith("https://"), f"{path} source url must start with https://"
        assert isinstance(source.get("quote_allowed"), bool), (
            f"{path} source quote_allowed must be boolean."
        )
        local_hash = source.get("local_artifact_sha256")
        if local_hash is not None:
            value = str(local_hash).strip().lower()
            assert re.fullmatch(r"[a-f0-9]{64}", value), (
                f"{path} local_artifact_sha256 must be a 64-char lowercase hex digest."
            )

    dimension_rationale = evidence_manifest.get("dimension_rationale")
    assert isinstance(dimension_rationale, dict), (
        f"{path} evidence_manifest.dimension_rationale must be an object."
    )
    assert set(dimension_rationale.keys()) == set(UNIFIED_DIMENSIONS), (
        f"{path} dimension_rationale keys mismatch. got={sorted(dimension_rationale.keys())}"
    )
    for dimension in UNIFIED_DIMENSIONS:
        entries = dimension_rationale.get(dimension)
        assert isinstance(entries, list) and entries, (
            f"{path} dimension_rationale['{dimension}'] must be a non-empty list."
        )
        for entry in entries:
            assert isinstance(entry, dict), (
                f"{path} rationale entry for '{dimension}' must be an object."
            )
            source_id = str(entry.get("source_id", "")).strip()
            assert source_id in source_ids, (
                f"{path} rationale for '{dimension}' references unknown source_id '{source_id}'."
            )
            claim = str(entry.get("claim", "")).strip()
            scoring_impact = str(entry.get("scoring_impact", "")).strip()
            assert claim, f"{path} rationale for '{dimension}' must include non-empty claim."
            assert scoring_impact, (
                f"{path} rationale for '{dimension}' must include non-empty scoring_impact."
            )


def test_case_study_files_are_present_and_schema_valid() -> None:
    case_dir = ROOT / "case_studies"
    assert case_dir.exists(), "case_studies directory is missing."

    for file_name in CASE_STUDY_FILES:
        path = case_dir / file_name
        assert path.exists(), f"Missing case study file: {path}"
        payload = _load_json(path)

        for required in (
            "id",
            "name",
            "description",
            "dimension_scores",
            "deployment_context",
            "evidence_manifest",
            "assumptions",
        ):
            assert required in payload, f"{path} missing required field '{required}'."

        dim_scores = payload["dimension_scores"]
        assert isinstance(dim_scores, dict), f"{path} dimension_scores must be an object."
        assert set(dim_scores.keys()) == set(UNIFIED_DIMENSIONS), (
            f"{path} dimension_scores keys mismatch. got={sorted(dim_scores.keys())}"
        )

        for dim in UNIFIED_DIMENSIONS:
            value = float(dim_scores[dim])
            assert LIKERT_MIN <= value <= LIKERT_MAX, (
                f"{path} score for {dim} out of range [{LIKERT_MIN}, {LIKERT_MAX}]"
            )

        _assert_evidence_manifest(path, payload["evidence_manifest"])
        _assert_non_empty_assumptions(path, payload["assumptions"])


def test_streamlit_case_studies_are_loaded_from_files() -> None:
    assert isinstance(CASE_STUDIES, list) and CASE_STUDIES, "CASE_STUDIES should be a non-empty list."
    ids = [str(item.get("id", "")) for item in CASE_STUDIES if isinstance(item, dict)]
    assert {"facial_recognition", "hiring_algorithm", "healthcare_diagnostic"}.issubset(set(ids))
