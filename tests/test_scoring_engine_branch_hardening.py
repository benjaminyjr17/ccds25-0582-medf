from __future__ import annotations

import runpy

import numpy as np
import pytest

from app import scoring_engine as se
from app.models import LIKERT_MAX, LIKERT_MIN, UNIFIED_DIMENSIONS


def _uniform_weights(n_dims: int) -> np.ndarray:
    return np.full(n_dims, 1.0 / n_dims, dtype=float)


def test_likert_scale_validators_cover_invalid_scales_and_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        se.likert_denominator(np.nan, LIKERT_MAX)

    with pytest.raises(ValueError, match="greater than"):
        se.likert_denominator(5.0, 5.0)

    with pytest.raises(ValueError, match="numeric"):
        se.validate_likert("oops", LIKERT_MIN, LIKERT_MAX)

    with pytest.raises(ValueError, match="finite"):
        se.validate_likert(np.inf, LIKERT_MIN, LIKERT_MAX)

    with pytest.raises(ValueError, match="within"):
        se.validate_likert(LIKERT_MAX + 1.0, LIKERT_MIN, LIKERT_MAX)


def test_topsis_rejects_invalid_weights_matrix_and_criteria_inputs() -> None:
    matrix = np.array([[2.0, 4.0], [4.0, 2.0]], dtype=float)

    with pytest.raises(ValueError, match="shape"):
        se.topsis_score(matrix, np.array([1.0], dtype=float), ["benefit", "benefit"])

    with pytest.raises(ValueError, match="finite"):
        se.topsis_score(matrix, np.array([0.5, np.nan], dtype=float), ["benefit", "benefit"])

    with pytest.raises(ValueError, match="non-negative"):
        se.topsis_score(matrix, np.array([1.0, -0.0 - 1.0], dtype=float), ["benefit", "benefit"])

    with pytest.raises(ValueError, match="all zero"):
        se.topsis_score(matrix, np.array([0.0, 0.0], dtype=float), ["benefit", "benefit"])

    with pytest.raises(ValueError, match="2D array"):
        se.topsis_score(np.array([1.0, 2.0], dtype=float), _uniform_weights(2), ["benefit", "benefit"])

    with pytest.raises(ValueError, match="at least one row"):
        se.topsis_score(np.empty((0, 2), dtype=float), _uniform_weights(2), ["benefit", "benefit"])

    with pytest.raises(ValueError, match="non-finite"):
        se.topsis_score(
            np.array([[2.0, np.nan], [3.0, 4.0]], dtype=float),
            _uniform_weights(2),
            ["benefit", "benefit"],
        )

    with pytest.raises(ValueError, match="within"):
        se.topsis_score(
            np.array([[0.0, 2.0], [3.0, 4.0]], dtype=float),
            _uniform_weights(2),
            ["benefit", "benefit"],
        )

    with pytest.raises(ValueError, match="exactly 2"):
        se.topsis_score(matrix, _uniform_weights(2), ["benefit"])

    with pytest.raises(ValueError, match="Invalid criteria_types"):
        se.topsis_score(matrix, _uniform_weights(2), ["benefit", "invalid"])

    with pytest.raises(ValueError, match="Zero column norms"):
        se.topsis_score(
            np.array([[LIKERT_MIN, 2.0], [LIKERT_MIN, 3.0]], dtype=float),
            _uniform_weights(2),
            ["benefit", "benefit"],
        )


def test_wsm_score_validates_vector_shape_finiteness_and_range() -> None:
    with pytest.raises(ValueError, match="1D"):
        se.wsm_score(np.array([[1.0, 2.0]], dtype=float), _uniform_weights(2))

    with pytest.raises(ValueError, match="non-finite"):
        se.wsm_score(np.array([1.0, np.nan], dtype=float), _uniform_weights(2))

    with pytest.raises(ValueError, match="within"):
        se.wsm_score(np.array([0.5, 2.0], dtype=float), _uniform_weights(2))


def test_ahp_weights_validates_matrix_shape_size_values_and_reciprocity_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="square"):
        se.ahp_weights(np.ones((2, 3), dtype=float))

    with pytest.raises(ValueError, match="between 3 and 10"):
        se.ahp_weights(np.ones((2, 2), dtype=float))

    with pytest.raises(ValueError, match="non-finite"):
        matrix = np.eye(3, dtype=float)
        matrix[0, 1] = np.nan
        se.ahp_weights(matrix)

    with pytest.raises(ValueError, match="positive"):
        matrix = np.eye(3, dtype=float)
        matrix[0, 1] = 0.0
        matrix[1, 0] = 0.0
        se.ahp_weights(matrix)

    near_consistent_not_reciprocal = np.array(
        [
            [1.0, 1.7, 2.4],
            [0.6, 1.0, 1.5],
            [0.4, 2.0 / 3.0, 1.0],
        ],
        dtype=float,
    )
    with pytest.warns(RuntimeWarning, match="not perfectly reciprocal"):
        weights, cr = se.ahp_weights(near_consistent_not_reciprocal)
    assert np.isclose(float(np.sum(weights)), 1.0, atol=1e-9)
    assert cr <= 0.10

    def _fake_eig(_: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.array([1.0, 0.5, 0.25], dtype=float),
            np.zeros((3, 3), dtype=float),
        )

    monkeypatch.setattr(se.np.linalg, "eig", _fake_eig)
    with pytest.raises(ValueError, match="principal eigenvector"):
        se.ahp_weights(np.ones((3, 3), dtype=float))


def test_compute_scores_covers_topsis_wsm_ahp_and_unsupported_method() -> None:
    dimension_scores = {dimension: 4.0 for dimension in UNIFIED_DIMENSIONS}
    weights = {dimension: 1.0 / len(UNIFIED_DIMENSIONS) for dimension in UNIFIED_DIMENSIONS}

    topsis = se.compute_scores(dimension_scores, weights, "topsis")
    wsm = se.compute_scores(dimension_scores, weights, "wsm")
    ahp = se.compute_scores(dimension_scores, weights, "ahp")

    for result in (topsis, wsm, ahp):
        assert 0.0 <= float(result["overall_score"]) <= 1.0
        assert set(result["dimension_scores"].keys()) == set(UNIFIED_DIMENSIONS)

    with pytest.raises(ValueError, match="Unsupported scoring method"):
        se.compute_scores(dimension_scores, weights, "not-a-method")


def test_scoring_engine_main_block_executes_without_error() -> None:
    runpy.run_module("app.scoring_engine", run_name="__main__")
