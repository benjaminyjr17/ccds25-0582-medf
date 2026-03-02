from __future__ import annotations

import numpy as np

from app.harm_assessment import _mean_pairwise_abs_diff, build_harm_assessment
from app.models import UNIFIED_DIMENSIONS


def _uniform_weight_map() -> dict[str, float]:
    n_dims = len(UNIFIED_DIMENSIONS)
    return {dimension: 1.0 / n_dims for dimension in UNIFIED_DIMENSIONS}


def test_mean_pairwise_abs_diff_returns_zeros_for_single_stakeholder() -> None:
    vector = np.array([[0.2, 0.3, 0.1, 0.1, 0.2, 0.1]], dtype=float)
    diffs = _mean_pairwise_abs_diff(vector)
    assert np.allclose(diffs, np.zeros(vector.shape[1], dtype=float), atol=1e-12)


def test_build_harm_assessment_uses_uniform_fallback_for_invalid_framework_sum() -> None:
    dimension_scores = {dimension: 4.0 for dimension in UNIFIED_DIMENSIONS}
    stakeholder_weights = {
        "developer": _uniform_weight_map(),
        "regulator": _uniform_weight_map(),
    }
    framework_weights = {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}

    result = build_harm_assessment(
        dimension_scores=dimension_scores,
        stakeholder_weights=stakeholder_weights,
        framework_weights=framework_weights,
    )

    assert 0.0 <= result.overall_score <= 1.0
    assert len(result.domain_scores) == len(UNIFIED_DIMENSIONS)
    assert set(result.top_risk_domains).issubset(set(UNIFIED_DIMENSIONS))
