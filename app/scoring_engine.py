from __future__ import annotations

import numpy as np

from app.models import UNIFIED_DIMENSIONS


def compute_scores(
    dimension_scores: dict[str, float],
    weights: dict[str, float],
    method: str,
) -> dict[str, float | dict[str, float]]:
    _ = method.lower().strip()

    # Stage 1C synthetic TOPSIS reference:
    # row 0 = AI system, row 1 = ideal (all 5), row 2 = worst (all 1).
    scores = np.array(
        [float(dimension_scores.get(dimension, 1.0)) for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    scores = np.clip(scores, 1.0, 5.0)

    weight_vector = np.array(
        [float(weights.get(dimension, 0.0)) for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    total_weight = float(weight_vector.sum())
    if total_weight <= 0.0:
        weight_vector = np.full(len(UNIFIED_DIMENSIONS), 1.0 / len(UNIFIED_DIMENSIONS), dtype=float)
    else:
        weight_vector = weight_vector / total_weight

    decision_matrix = np.vstack(
        [
            scores,
            np.full(len(UNIFIED_DIMENSIONS), 5.0, dtype=float),
            np.full(len(UNIFIED_DIMENSIONS), 1.0, dtype=float),
        ]
    )

    norms = np.linalg.norm(decision_matrix, axis=0)
    norms[norms == 0.0] = 1.0
    normalized = decision_matrix / norms
    weighted = normalized * weight_vector

    ideal = np.max(weighted, axis=0)
    worst = np.min(weighted, axis=0)
    ai_row = weighted[0]

    distance_to_ideal = np.abs(ai_row - ideal)
    distance_to_worst = np.abs(ai_row - worst)

    d_plus = float(np.linalg.norm(distance_to_ideal))
    d_minus = float(np.linalg.norm(distance_to_worst))
    overall_score = d_minus / (d_plus + d_minus) if (d_plus + d_minus) > 0.0 else 0.0

    # Criterion-level weighted closeness contributions for downstream ranking/inspection.
    per_dimension_array = np.divide(
        distance_to_worst,
        distance_to_ideal + distance_to_worst,
        out=np.zeros_like(distance_to_worst),
        where=(distance_to_ideal + distance_to_worst) > 0.0,
    ) * weight_vector

    per_dimension = {
        dimension: float(per_dimension_array[index])
        for index, dimension in enumerate(UNIFIED_DIMENSIONS)
    }

    overall_score = min(max(float(overall_score), 0.0), 1.0)

    return {
        "overall_score": overall_score,
        "dimension_scores": per_dimension,
    }
