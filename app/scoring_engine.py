from __future__ import annotations

import warnings

import numpy as np

from app.models import UNIFIED_DIMENSIONS

_WEIGHT_SUM_TOLERANCE = 1e-6
_RECIPROCAL_TOLERANCE = 1e-3
_VALID_CRITERIA_TYPES = {"benefit", "cost"}
_AHP_RANDOM_INDEX: dict[int, float] = {
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


def _validate_scale(scale_min: float, scale_max: float) -> None:
    if not np.isfinite(scale_min) or not np.isfinite(scale_max):
        raise ValueError("scale_min and scale_max must be finite.")
    if scale_max <= scale_min:
        raise ValueError("scale_max must be greater than scale_min.")


def _validate_weights(weights: np.ndarray, n_dims: int) -> np.ndarray:
    validated = np.asarray(weights, dtype=float)
    if validated.ndim != 1 or validated.shape[0] != n_dims:
        raise ValueError(f"weights must have shape ({n_dims},).")
    if not np.all(np.isfinite(validated)):
        raise ValueError("weights must contain only finite values.")
    if np.any(validated < 0.0):
        raise ValueError("weights must be non-negative.")
    if np.allclose(validated, 0.0):
        raise ValueError("weights cannot be all zero.")

    total = float(validated.sum())
    if not np.isclose(total, 1.0, atol=_WEIGHT_SUM_TOLERANCE):
        raise ValueError(
            f"weights must sum to 1.0 (±{_WEIGHT_SUM_TOLERANCE}); got {total:.8f}."
        )
    return validated


def _validate_decision_matrix(
    decision_matrix: np.ndarray,
    *,
    scale_min: float,
    scale_max: float,
) -> np.ndarray:
    matrix = np.asarray(decision_matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("decision_matrix must be a 2D array with shape (n_alts, n_dims).")
    if matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("decision_matrix must have at least one row and one column.")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("decision_matrix contains non-finite values.")
    if np.any(matrix < scale_min) or np.any(matrix > scale_max):
        raise ValueError(
            f"decision_matrix values must be within [{scale_min}, {scale_max}]."
        )
    return matrix


def topsis_score(
    decision_matrix: np.ndarray,
    weights: np.ndarray,
    criteria_types: list[str],
    *,
    scale_min: float = 1.0,
    scale_max: float = 5.0,
    return_debug: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, np.ndarray | list[str] | float]]:
    _validate_scale(scale_min, scale_max)
    matrix = _validate_decision_matrix(
        decision_matrix,
        scale_min=scale_min,
        scale_max=scale_max,
    )
    n_alts, n_dims = matrix.shape

    validated_weights = _validate_weights(weights, n_dims)

    if len(criteria_types) != n_dims:
        raise ValueError(f"criteria_types must contain exactly {n_dims} entries.")

    normalized_types = [str(criteria).strip().lower() for criteria in criteria_types]
    invalid_types = [criteria for criteria in normalized_types if criteria not in _VALID_CRITERIA_TYPES]
    if invalid_types:
        raise ValueError(
            f"Invalid criteria_types detected: {invalid_types}. Allowed values are 'benefit' or 'cost'."
        )

    # Step 1: scale raw Likert scores into [0, 1].
    X_scaled = (matrix - scale_min) / (scale_max - scale_min)

    # Step 2: vector normalization.
    norms = np.linalg.norm(X_scaled, axis=0)
    if np.any(norms == 0.0):
        raise ValueError("Zero column norms detected during TOPSIS normalization.")
    R = X_scaled / norms

    # Step 3: weighted normalized decision matrix.
    V = R * validated_weights

    # Step 4: ideal best/worst points based on criterion type.
    benefit_mask = np.array([criteria == "benefit" for criteria in normalized_types], dtype=bool)
    ideal_best = np.where(benefit_mask, np.max(V, axis=0), np.min(V, axis=0))
    ideal_worst = np.where(benefit_mask, np.min(V, axis=0), np.max(V, axis=0))

    # Step 5: Euclidean distances to the ideal solutions.
    d_best = np.linalg.norm(V - ideal_best, axis=1)
    d_worst = np.linalg.norm(V - ideal_worst, axis=1)
    denom = d_best + d_worst

    # Step 6: closeness coefficient in [0, 1].
    scores = np.divide(
        d_worst,
        denom,
        out=np.zeros(n_alts, dtype=float),
        where=denom > 0.0,
    )
    scores = np.clip(scores, 0.0, 1.0)

    if not return_debug:
        return scores

    debug: dict[str, np.ndarray | list[str] | float] = {
        "X_raw": matrix.copy(),
        "X_scaled": X_scaled,
        "norms": norms,
        "R": R,
        "V": V,
        "ideal_best": ideal_best,
        "ideal_worst": ideal_worst,
        "d_best": d_best,
        "d_worst": d_worst,
        "criteria_types": normalized_types,
        "weights": validated_weights.copy(),
        "scale_min": float(scale_min),
        "scale_max": float(scale_max),
    }
    return scores, debug


def wsm_score(
    scores: np.ndarray,
    weights: np.ndarray,
    *,
    scale_min: float = 1.0,
    scale_max: float = 5.0,
) -> float:
    _validate_scale(scale_min, scale_max)
    vector = np.asarray(scores, dtype=float)
    if vector.ndim != 1:
        raise ValueError("scores must be a 1D array with shape (n_dims,).")
    if not np.all(np.isfinite(vector)):
        raise ValueError("scores contains non-finite values.")
    if np.any(vector < scale_min) or np.any(vector > scale_max):
        raise ValueError(f"scores must be within [{scale_min}, {scale_max}].")

    validated_weights = _validate_weights(weights, vector.shape[0])

    scaled = (vector - scale_min) / (scale_max - scale_min)
    weighted_sum = float(np.dot(scaled, validated_weights))
    return float(np.clip(weighted_sum, 0.0, 1.0))


def wsm_scores(
    decision_matrix: np.ndarray,
    weights: np.ndarray,
    *,
    scale_min: float = 1.0,
    scale_max: float = 5.0,
) -> np.ndarray:
    _validate_scale(scale_min, scale_max)
    matrix = _validate_decision_matrix(
        decision_matrix,
        scale_min=scale_min,
        scale_max=scale_max,
    )
    validated_weights = _validate_weights(weights, matrix.shape[1])
    scaled = (matrix - scale_min) / (scale_max - scale_min)
    totals = scaled @ validated_weights
    return np.clip(totals, 0.0, 1.0)


def ahp_weights(pairwise_matrix: np.ndarray) -> tuple[np.ndarray, float]:
    matrix = np.asarray(pairwise_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("pairwise_matrix must be square with shape (n, n).")

    n = matrix.shape[0]
    if n < 3 or n > 10:
        raise ValueError("pairwise_matrix size must be between 3 and 10.")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("pairwise_matrix contains non-finite values.")
    if np.any(matrix <= 0.0):
        raise ValueError("pairwise_matrix must contain only positive values.")

    reciprocal_target = 1.0 / matrix.T
    if not np.allclose(matrix, reciprocal_target, rtol=_RECIPROCAL_TOLERANCE, atol=_RECIPROCAL_TOLERANCE):
        warnings.warn(
            "pairwise_matrix is not perfectly reciprocal; proceeding with eigenvector method.",
            RuntimeWarning,
            stacklevel=2,
        )

    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    max_index = int(np.argmax(eigenvalues.real))
    lambda_max = float(eigenvalues.real[max_index])

    principal = np.abs(eigenvectors[:, max_index].real)
    principal_sum = float(principal.sum())
    if principal_sum <= 0.0:
        raise ValueError("Unable to derive a valid principal eigenvector for AHP weights.")

    weights = principal / principal_sum

    ci = (lambda_max - n) / (n - 1)
    ri = _AHP_RANDOM_INDEX[n]
    cr = float(ci / ri) if ri > 0.0 else 0.0

    if cr > 0.10:
        raise ValueError(
            f"AHP consistency ratio too high: CR={cr:.4f} exceeds threshold 0.10."
        )

    return weights.astype(float), float(max(cr, 0.0))


def compute_scores(
    dimension_scores: dict[str, float],
    weights: dict[str, float],
    method: str,
) -> dict[str, float | dict[str, float]]:
    method_key = method.lower().strip()
    score_vector = np.array(
        [float(dimension_scores.get(dimension, 1.0)) for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    weight_vector = np.array(
        [float(weights.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    validated_weights = _validate_weights(weight_vector, len(UNIFIED_DIMENSIONS))

    if method_key == "topsis":
        decision_matrix = np.vstack(
            [
                score_vector,
                np.full(len(UNIFIED_DIMENSIONS), 5.0, dtype=float),
                np.full(len(UNIFIED_DIMENSIONS), 1.0, dtype=float),
            ]
        )
        topsis_values, debug = topsis_score(
            decision_matrix=decision_matrix,
            weights=validated_weights,
            criteria_types=["benefit"] * len(UNIFIED_DIMENSIONS),
            return_debug=True,
        )
        overall_score = float(topsis_values[0])
        weighted_row = np.asarray(debug["V"])[0]
        ideal_best = np.asarray(debug["ideal_best"])
        ideal_worst = np.asarray(debug["ideal_worst"])
        d_best = np.abs(weighted_row - ideal_best)
        d_worst = np.abs(weighted_row - ideal_worst)
        denom = d_best + d_worst
        per_dimension_array = np.divide(
            d_worst,
            denom,
            out=np.zeros_like(d_worst),
            where=denom > 0.0,
        ) * validated_weights
    elif method_key in {"wsm", "ahp"}:
        overall_score = float(wsm_score(score_vector, validated_weights))
        scaled = (score_vector - 1.0) / 4.0
        per_dimension_array = np.clip(scaled * validated_weights, 0.0, 1.0)
    else:
        raise ValueError(f"Unsupported scoring method '{method_key}'.")

    overall_score = min(max(float(overall_score), 0.0), 1.0)
    per_dimension = {
        dimension: float(per_dimension_array[index])
        for index, dimension in enumerate(UNIFIED_DIMENSIONS)
    }

    return {
        "overall_score": overall_score,
        "dimension_scores": per_dimension,
    }


if __name__ == "__main__":
    facial_recognition = np.array([[2.0, 1.0, 4.0, 1.0, 2.0, 3.0]], dtype=float)
    developer_weights = np.array([0.10, 0.15, 0.30, 0.15, 0.15, 0.15], dtype=float)
    criteria = ["benefit"] * len(UNIFIED_DIMENSIONS)

    decision = np.vstack(
        [
            facial_recognition[0],
            np.full(len(UNIFIED_DIMENSIONS), 5.0, dtype=float),
            np.full(len(UNIFIED_DIMENSIONS), 1.0, dtype=float),
        ]
    )

    scores, debug_info = topsis_score(
        decision_matrix=decision,
        weights=developer_weights,
        criteria_types=criteria,
        return_debug=True,
    )

    print("Dimensions:", list(UNIFIED_DIMENSIONS))
    print("TOPSIS score (facial recognition):", round(float(scores[0]), 4))
    print("Norms:", np.array2string(np.asarray(debug_info["norms"]), precision=4))
    print("Ideal best:", np.array2string(np.asarray(debug_info["ideal_best"]), precision=4))
    print("Ideal worst:", np.array2string(np.asarray(debug_info["ideal_worst"]), precision=4))
