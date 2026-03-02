from __future__ import annotations

import pytest

from app.framework_registry import _parse_dimensions
from app.models import UNIFIED_DIMENSIONS


BASE_WEIGHT = 1.0 / len(UNIFIED_DIMENSIONS)


def _raw_dimension(
    dimension_id: str,
    *,
    weight: float = BASE_WEIGHT,
    criteria_type: str = "benefit",
    assessment_questions: list[str] | object | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "dimension": dimension_id,
        "name": dimension_id.replace("_", " ").title(),
        "weight": weight,
        "criteria_type": criteria_type,
    }
    if assessment_questions is not None:
        payload["assessment_questions"] = assessment_questions
    return payload


def _full_dimension_list(*, weight: float = BASE_WEIGHT) -> list[dict[str, object]]:
    return [
        _raw_dimension(dimension_id, weight=weight, assessment_questions=["q1", "q2"])
        for dimension_id in UNIFIED_DIMENSIONS
    ]


def test_parse_dimensions_rejects_missing_dimensions_list() -> None:
    with pytest.raises(RuntimeError, match="must contain a 'dimensions' or 'criteria' list"):
        _parse_dimensions({}, "broken.yaml")


def test_parse_dimensions_rejects_invalid_criteria_type() -> None:
    dimensions = _full_dimension_list()
    dimensions[0]["criteria_type"] = "invalid"

    with pytest.raises(RuntimeError, match="Invalid criteria_type"):
        _parse_dimensions({"dimensions": dimensions}, "broken.yaml")


def test_parse_dimensions_rejects_non_list_assessment_questions() -> None:
    dimensions = _full_dimension_list()
    dimensions[0]["assessment_questions"] = "not-a-list"

    with pytest.raises(RuntimeError, match="Invalid assessment_questions"):
        _parse_dimensions({"dimensions": dimensions}, "broken.yaml")


def test_parse_dimensions_rejects_missing_canonical_dimensions() -> None:
    incomplete = [_raw_dimension(UNIFIED_DIMENSIONS[0], assessment_questions=["q"])]

    with pytest.raises(RuntimeError, match="missing canonical dimensions"):
        _parse_dimensions({"dimensions": incomplete}, "broken.yaml")


def test_parse_dimensions_rejects_dimension_default_weight_sum_not_one() -> None:
    overweight_dimensions = _full_dimension_list(weight=0.2)

    with pytest.raises(RuntimeError, match="weights must sum to 1.0"):
        _parse_dimensions({"dimensions": overweight_dimensions}, "broken.yaml")
