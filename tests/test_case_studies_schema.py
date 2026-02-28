from __future__ import annotations

import json
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
    if isinstance(assumptions, str):
        assert assumptions.strip(), f"{path} assumptions must not be empty."
        return
    if isinstance(assumptions, list):
        assert assumptions, f"{path} assumptions list must not be empty."
        assert all(
            isinstance(item, str) and item.strip() for item in assumptions
        ), f"{path} assumptions list entries must be non-empty strings."
        return
    raise AssertionError(f"{path} assumptions must be a non-empty string or list of strings.")


def _assert_source_reference(path: Path, source_reference: Any) -> None:
    if isinstance(source_reference, str):
        assert source_reference.strip(), f"{path} source_reference string must not be empty."
        return
    if isinstance(source_reference, dict):
        citation = str(source_reference.get("citation", "")).strip()
        url = str(source_reference.get("url", "")).strip()
        assert citation or url, f"{path} source_reference must include citation or url."
        if url:
            assert url.startswith(("http://", "https://")), (
                f"{path} source_reference.url must start with http:// or https://"
            )
        return
    raise AssertionError(f"{path} source_reference must be a non-empty string or object.")


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
            "source_reference",
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

        _assert_source_reference(path, payload["source_reference"])
        _assert_non_empty_assumptions(path, payload["assumptions"])


def test_streamlit_case_studies_are_loaded_from_files() -> None:
    assert isinstance(CASE_STUDIES, list) and CASE_STUDIES, "CASE_STUDIES should be a non-empty list."
    ids = [str(item.get("id", "")) for item in CASE_STUDIES if isinstance(item, dict)]
    assert {"facial_recognition", "hiring_algorithm", "healthcare_diagnostic"}.issubset(set(ids))
