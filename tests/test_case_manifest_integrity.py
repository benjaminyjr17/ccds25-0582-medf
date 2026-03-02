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


def _load_case(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict), f"{path} must be a JSON object."
    return payload


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


def test_case_manifest_quote_policy_is_consistent() -> None:
    case_dir = ROOT / "case_studies"

    for file_name in CASE_FILES:
        payload = _load_case(case_dir / file_name)
        manifest = payload.get("evidence_manifest")
        assert isinstance(manifest, dict), f"{file_name} evidence_manifest must be an object."
        sources = manifest.get("sources")
        assert isinstance(sources, list), f"{file_name} evidence_manifest.sources must be a list."

        for source in sources:
            assert isinstance(source, dict), f"{file_name} source entry must be an object."
            quote_allowed = source.get("quote_allowed")
            assert isinstance(quote_allowed, bool), (
                f"{file_name} source quote_allowed must be boolean."
            )
            if not quote_allowed:
                assert "excerpt" not in source, (
                    f"{file_name} source '{source.get('source_id')}' must not include excerpts when quote_allowed=false."
                )
