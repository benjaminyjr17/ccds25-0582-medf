from __future__ import annotations

import numpy as np
import pytest

from app.scoring_engine import ahp_weights, topsis_score, wsm_score, wsm_scores


def test_topsis_shape_and_range_multiple_alternatives() -> None:
    decision_matrix = np.array(
        [
            [2.0, 1.0, 4.0, 1.0, 2.0, 3.0],
            [4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
        ],
        dtype=float,
    )
    weights = np.array([0.10, 0.15, 0.30, 0.15, 0.15, 0.15], dtype=float)
    criteria_types = ["benefit"] * 6

    scores = topsis_score(decision_matrix, weights, criteria_types)

    assert scores.shape == (2,)
    assert np.all(scores >= 0.0)
    assert np.all(scores <= 1.0)


def test_topsis_weights_sum_validation() -> None:
    decision_matrix = np.array([[2.0, 2.0, 3.0, 2.0, 3.0, 4.0]], dtype=float)
    weights = np.array([0.10, 0.15, 0.30, 0.15, 0.15, 0.25], dtype=float)

    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        topsis_score(decision_matrix, weights, ["benefit"] * 6)


def test_topsis_cost_criterion_behavior() -> None:
    decision_matrix = np.array(
        [
            [1.0, 7.0],
            [7.0, 6.0],
        ],
        dtype=float,
    )
    weights = np.array([0.5, 0.5], dtype=float)
    scores, debug = topsis_score(
        decision_matrix,
        weights,
        ["benefit", "cost"],
        return_debug=True,
    )
    weighted_matrix = np.asarray(debug["V"])
    ideal_best = np.asarray(debug["ideal_best"])
    ideal_worst = np.asarray(debug["ideal_worst"])

    assert scores.shape == (2,)
    assert ideal_best[1] == pytest.approx(np.min(weighted_matrix[:, 1]))
    assert ideal_worst[1] == pytest.approx(np.max(weighted_matrix[:, 1]))


def test_wsm_simple() -> None:
    scores = np.array([1.0, 7.0], dtype=float)
    weights = np.array([0.25, 0.75], dtype=float)

    value = wsm_score(scores, weights)

    assert value == pytest.approx(0.75, abs=1e-9)


def test_wsm_scores_multiple_rows() -> None:
    decision_matrix = np.array(
        [
            [1.0, 1.0, 1.0],
            [7.0, 7.0, 7.0],
        ],
        dtype=float,
    )
    weights = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=float)

    values = wsm_scores(decision_matrix, weights)

    assert values.shape == (2,)
    assert values[0] == pytest.approx(0.0, abs=1e-9)
    assert values[1] == pytest.approx(1.0, abs=1e-9)


def test_ahp_consistent_matrix_cr_small() -> None:
    pairwise_matrix = np.array(
        [
            [1.0, 0.5 / 0.3, 0.5 / 0.2],
            [0.3 / 0.5, 1.0, 0.3 / 0.2],
            [0.2 / 0.5, 0.2 / 0.3, 1.0],
        ],
        dtype=float,
    )

    weights, cr = ahp_weights(pairwise_matrix)

    assert weights.sum() == pytest.approx(1.0, abs=1e-9)
    assert cr <= 0.10
    assert np.all(weights >= 0.0)


def test_ahp_inconsistent_matrix_rejected() -> None:
    pairwise_matrix = np.array(
        [
            [1.0, 9.0, 1.0 / 9.0],
            [1.0 / 9.0, 1.0, 9.0],
            [9.0, 1.0 / 9.0, 1.0],
        ],
        dtype=float,
    )

    with pytest.raises(ValueError, match="CR=.*0.10"):
        ahp_weights(pairwise_matrix)
