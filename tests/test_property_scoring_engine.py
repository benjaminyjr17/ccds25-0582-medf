from __future__ import annotations

import numpy as np
import pytest
from hypothesis import assume, given, settings, strategies as st

from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS
from app.scoring_engine import (
    ahp_weights,
    normalize_likert,
    topsis_score,
    wsm_scores,
)


pytestmark = [pytest.mark.extreme, pytest.mark.property]

N_DIMS = len(UNIFIED_DIMENSIONS)


def _simplex_strategy(size: int) -> st.SearchStrategy[np.ndarray]:
    return st.lists(
        st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=size,
        max_size=size,
    ).map(lambda values: np.asarray(values, dtype=float)).map(lambda arr: arr / float(np.sum(arr)))


@st.composite
def _decision_matrix_strategy(draw) -> np.ndarray:
    rows = draw(st.integers(min_value=2, max_value=6))
    values = draw(
        st.lists(
            st.floats(
                min_value=LIKERT_MIN,
                max_value=LIKERT_MAX,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=rows * N_DIMS,
            max_size=rows * N_DIMS,
        )
    )
    matrix = np.asarray(values, dtype=float).reshape(rows, N_DIMS)

    # Avoid degenerate all-min columns that trigger zero-norm TOPSIS rejection.
    assume(np.all(np.max(matrix, axis=0) > LIKERT_MIN))
    return matrix


@st.composite
def _criteria_types_strategy(draw) -> list[str]:
    return draw(
        st.lists(st.sampled_from(["benefit", "cost"]), min_size=N_DIMS, max_size=N_DIMS)
    )


@st.composite
def _consistent_ahp_matrix(draw) -> np.ndarray:
    n = draw(st.integers(min_value=3, max_value=6))
    weight_vector = draw(_simplex_strategy(n))
    matrix = np.outer(weight_vector, 1.0 / weight_vector)
    return matrix.astype(float)


@given(st.floats(min_value=LIKERT_MIN, max_value=LIKERT_MAX, allow_nan=False, allow_infinity=False))
@settings(max_examples=120)
def test_property_normalize_likert_is_bounded(value: float) -> None:
    normalized = normalize_likert(value, LIKERT_MIN, LIKERT_MAX)
    assert 0.0 <= normalized <= 1.0


@given(
    decision_matrix=_decision_matrix_strategy(),
    weights=_simplex_strategy(N_DIMS),
    criteria_types=_criteria_types_strategy(),
)
@settings(max_examples=60)
def test_property_topsis_scores_are_finite_bounded_and_deterministic(
    decision_matrix: np.ndarray,
    weights: np.ndarray,
    criteria_types: list[str],
) -> None:
    scores_first = topsis_score(
        decision_matrix=decision_matrix,
        weights=weights,
        criteria_types=criteria_types,
        scale_min=LIKERT_MIN,
        scale_max=LIKERT_MAX,
    )
    scores_second = topsis_score(
        decision_matrix=decision_matrix,
        weights=weights,
        criteria_types=criteria_types,
        scale_min=LIKERT_MIN,
        scale_max=LIKERT_MAX,
    )

    assert np.all(np.isfinite(scores_first))
    assert np.all(scores_first >= 0.0)
    assert np.all(scores_first <= 1.0)
    assert np.allclose(scores_first, scores_second)


@given(
    decision_matrix=_decision_matrix_strategy(),
    weights=_simplex_strategy(N_DIMS),
)
@settings(max_examples=60)
def test_property_wsm_scores_are_finite_and_bounded(
    decision_matrix: np.ndarray,
    weights: np.ndarray,
) -> None:
    scores = wsm_scores(
        decision_matrix=decision_matrix,
        weights=weights,
        scale_min=LIKERT_MIN,
        scale_max=LIKERT_MAX,
    )
    assert np.all(np.isfinite(scores))
    assert np.all(scores >= 0.0)
    assert np.all(scores <= 1.0)


def test_property_invalid_criteria_types_raise_value_error() -> None:
    decision_matrix = np.asarray(
        [
            [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            [3.0, 4.0, 5.0, 6.0, 7.0, 1.0],
            [4.0, 5.0, 6.0, 7.0, 1.0, 2.0],
        ],
        dtype=float,
    )
    weights = np.asarray([1.0 / N_DIMS] * N_DIMS, dtype=float)
    criteria_types = ["benefit"] * (N_DIMS - 1) + ["invalid"]

    with pytest.raises(ValueError, match="Invalid criteria_types"):
        topsis_score(
            decision_matrix=decision_matrix,
            weights=weights,
            criteria_types=criteria_types,
        )


@given(pairwise_matrix=_consistent_ahp_matrix())
@settings(max_examples=60)
def test_property_ahp_consistent_matrices_produce_normalized_weights(
    pairwise_matrix: np.ndarray,
) -> None:
    weights, cr = ahp_weights(pairwise_matrix)
    assert np.all(np.isfinite(weights))
    assert abs(float(np.sum(weights)) - 1.0) <= 1e-8
    assert cr <= 0.10
