from __future__ import annotations

from app.models import UNIFIED_DIMENSIONS


def _normalize_score(value: float) -> float:
    normalized = (value - 1.0) / 4.0
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return normalized


def compute_scores(
    dimension_scores: dict[str, float],
    weights: dict[str, float],
    method: str,
) -> dict[str, float | dict[str, float]]:
    _ = method

    per_dimension: dict[str, float] = {}
    overall_score = 0.0

    for dimension in UNIFIED_DIMENSIONS:
        raw_dimension_score = float(dimension_scores.get(dimension, 1.0))
        normalized = _normalize_score(raw_dimension_score)
        weight = float(weights.get(dimension, 0.0))
        weighted_score = normalized * weight

        per_dimension[dimension] = weighted_score
        overall_score += weighted_score

    if overall_score < 0.0:
        overall_score = 0.0
    if overall_score > 1.0:
        overall_score = 1.0

    return {
        "overall_score": overall_score,
        "dimension_scores": per_dimension,
    }
