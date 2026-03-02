from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS
from streamlit_app import CASE_STUDIES, CASE_STUDY_FILES


ROOT = Path(__file__).resolve().parent.parent
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
EXCERPT_MAX_CHARS = 280


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


def _clean_optional_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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
            "publisher",
            "published_at",
            "retrieved_at",
            "primary_url",
            "archived_url",
            "doi_or_stable_id",
            "license",
            "quote_allowed",
            "excerpt",
            "sha256",
        ):
            assert required in source, f"{path} source missing required field '{required}'."

        source_id = str(source.get("source_id", "")).strip()
        assert source_id, f"{path} source_id must be non-empty."
        assert source_id not in source_ids, f"{path} duplicate source_id '{source_id}'."
        source_ids.add(source_id)

        published_at = str(source.get("published_at", "")).strip()
        retrieved_at = str(source.get("retrieved_at", "")).strip()
        assert ISO_DATE_PATTERN.fullmatch(published_at), (
            f"{path} source '{source_id}' published_at must use YYYY-MM-DD format."
        )
        assert ISO_DATE_PATTERN.fullmatch(retrieved_at), (
            f"{path} source '{source_id}' retrieved_at must use YYYY-MM-DD format."
        )

        primary_url = str(source.get("primary_url", "")).strip()
        assert primary_url.startswith("https://"), (
            f"{path} source '{source_id}' primary_url must start with https://"
        )

        archived_url = _clean_optional_text(source.get("archived_url"))
        if archived_url:
            assert archived_url.startswith("https://"), (
                f"{path} source '{source_id}' archived_url must start with https:// when provided."
            )

        stable_id = _clean_optional_text(source.get("doi_or_stable_id"))
        local_snapshot_path = _clean_optional_text(source.get("local_snapshot_path"))
        assert archived_url or stable_id or local_snapshot_path, (
            f"{path} source '{source_id}' must include archived_url, doi_or_stable_id, or local_snapshot_path."
        )

        license_label = str(source.get("license", "")).strip()
        assert license_label, f"{path} source '{source_id}' license must be non-empty."

        quote_allowed = source.get("quote_allowed")
        assert isinstance(quote_allowed, bool), (
            f"{path} source '{source_id}' quote_allowed must be boolean."
        )
        excerpt = source.get("excerpt")
        if quote_allowed:
            if excerpt is not None:
                assert isinstance(excerpt, str), (
                    f"{path} source '{source_id}' excerpt must be string or null."
                )
                cleaned_excerpt = excerpt.strip()
                assert cleaned_excerpt, (
                    f"{path} source '{source_id}' excerpt must be non-empty when provided."
                )
                assert len(cleaned_excerpt) <= EXCERPT_MAX_CHARS, (
                    f"{path} source '{source_id}' excerpt exceeds {EXCERPT_MAX_CHARS} chars."
                )
        else:
            assert excerpt in (None, ""), (
                f"{path} source '{source_id}' must not include excerpt when quote_allowed=false."
            )

        sha256_value = _clean_optional_text(source.get("sha256")).lower()
        if sha256_value:
            assert SHA256_PATTERN.fullmatch(sha256_value), (
                f"{path} source '{source_id}' sha256 must be a 64-char lowercase hex digest."
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
            cited_ids = entry.get("source_ids")
            assert isinstance(cited_ids, list) and cited_ids, (
                f"{path} rationale for '{dimension}' must include non-empty source_ids list."
            )
            cleaned_ids = [str(item).strip() for item in cited_ids if str(item).strip()]
            assert cleaned_ids, f"{path} rationale for '{dimension}' must cite at least one source_id."
            for source_id in cleaned_ids:
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


def test_real_deployment_targets_do_not_use_synthetic_or_deployment_like_wording() -> None:
    banned_terms = ("synthetic", "deployment-like")
    targets: list[Path] = [
        ROOT / "docs" / "scope_boundary.md",
        ROOT / "docs" / "requirements_traceability.md",
    ]

    case_dir = ROOT / "case_studies"
    for file_name in CASE_STUDY_FILES:
        path = case_dir / file_name
        payload = _load_json(path)
        manifest = payload.get("evidence_manifest")
        deployment_type = ""
        if isinstance(manifest, dict):
            deployment_type = str(manifest.get("deployment_type", "")).strip()
        if deployment_type == "real_deployment":
            targets.append(path)

    for path in targets:
        text = path.read_text(encoding="utf-8").lower()
        for term in banned_terms:
            assert term not in text, f"Found banned term '{term}' in {path}."
