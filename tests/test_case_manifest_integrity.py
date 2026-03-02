from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CASE_FILES: tuple[str, ...] = (
    "facial_recognition.json",
    "hiring_algorithm.json",
    "healthcare_diagnostic.json",
)
EXCERPT_MAX_CHARS = 280


def _load_case(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict), f"{path} must be a JSON object."
    return payload


def _normalize_optional(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def test_case_evidence_readmes_exist_for_all_cases() -> None:
    case_dir = ROOT / "case_studies"
    evidence_dir = ROOT / "docs" / "case_evidence"

    for file_name in CASE_FILES:
        payload = _load_case(case_dir / file_name)
        case_id = str(payload.get("id", "")).strip()
        assert case_id, f"{file_name} must include non-empty id."
        readme = evidence_dir / case_id / "README.md"
        assert readme.exists(), f"Missing evidence README for case '{case_id}': {readme}"
        text = readme.read_text(encoding="utf-8").strip()
        assert text, f"Evidence README for case '{case_id}' is empty: {readme}"


def test_case_manifest_quote_policy_and_resolver_coverage() -> None:
    case_dir = ROOT / "case_studies"

    for file_name in CASE_FILES:
        payload = _load_case(case_dir / file_name)
        manifest = payload.get("evidence_manifest")
        assert isinstance(manifest, dict), f"{file_name} evidence_manifest must be an object."
        sources = manifest.get("sources")
        assert isinstance(sources, list), f"{file_name} evidence_manifest.sources must be a list."

        source_ids = {
            str(source.get("source_id", "")).strip()
            for source in sources
            if isinstance(source, dict) and str(source.get("source_id", "")).strip()
        }
        assert source_ids, f"{file_name} must include at least one source_id."

        for source in sources:
            assert isinstance(source, dict), f"{file_name} source entry must be an object."
            source_id = str(source.get("source_id", "")).strip()
            quote_allowed = source.get("quote_allowed")
            assert isinstance(quote_allowed, bool), (
                f"{file_name} source '{source_id}' quote_allowed must be boolean."
            )

            excerpt = source.get("excerpt")
            if quote_allowed:
                if excerpt is not None:
                    assert isinstance(excerpt, str), (
                        f"{file_name} source '{source_id}' excerpt must be string or null."
                    )
                    assert excerpt.strip(), (
                        f"{file_name} source '{source_id}' excerpt must be non-empty when provided."
                    )
                    assert len(excerpt.strip()) <= EXCERPT_MAX_CHARS, (
                        f"{file_name} source '{source_id}' excerpt exceeds {EXCERPT_MAX_CHARS} chars."
                    )
            else:
                assert excerpt in (None, ""), (
                    f"{file_name} source '{source_id}' must not include excerpts when quote_allowed=false."
                )

            archived_url = _normalize_optional(source.get("archived_url"))
            stable_id = _normalize_optional(source.get("doi_or_stable_id"))
            local_snapshot_path = _normalize_optional(source.get("local_snapshot_path"))
            assert archived_url or stable_id or local_snapshot_path, (
                f"{file_name} source '{source_id}' must include archived_url, doi_or_stable_id, or local_snapshot_path."
            )

        rationale = manifest.get("dimension_rationale")
        assert isinstance(rationale, dict), (
            f"{file_name} evidence_manifest.dimension_rationale must be an object."
        )
        for dimension, entries in rationale.items():
            assert isinstance(entries, list) and entries, (
                f"{file_name} rationale for '{dimension}' must be a non-empty list."
            )
            for entry in entries:
                assert isinstance(entry, dict), (
                    f"{file_name} rationale entry for '{dimension}' must be an object."
                )
                cited_ids = entry.get("source_ids")
                assert isinstance(cited_ids, list) and cited_ids, (
                    f"{file_name} rationale for '{dimension}' must include source_ids."
                )
                for cited_id in cited_ids:
                    resolved = str(cited_id).strip()
                    assert resolved in source_ids, (
                        f"{file_name} rationale for '{dimension}' references unknown source_id '{resolved}'."
                    )
