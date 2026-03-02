from __future__ import annotations

from itertools import combinations

import numpy as np

from app.models import (
    HarmAssessment,
    HarmDomainScore,
    HarmSeverity,
    UNIFIED_DIMENSIONS,
)
from app.scoring_engine import normalize_likert

MODEL_VERSION = "harm_taxonomy_v1"

_HARM_DOMAIN_MAP: tuple[tuple[str, str], ...] = (
    ("opacity_harm", "transparency_explainability"),
    ("discrimination_harm", "fairness_nondiscrimination"),
    ("safety_failure_harm", "safety_robustness"),
    ("privacy_intrusion_harm", "privacy_data_governance"),
    ("autonomy_oversight_harm", "human_agency_oversight"),
    ("accountability_redress_harm", "accountability"),
)

_ALPHA_BASE_RISK = 0.7
_BETA_DISAGREEMENT = 0.3


def _severity(score: float) -> HarmSeverity:
    if score < 0.25:
        return HarmSeverity.LOW
    if score < 0.50:
        return HarmSeverity.MODERATE
    if score < 0.75:
        return HarmSeverity.HIGH
    return HarmSeverity.CRITICAL


def _mean_pairwise_abs_diff(stakeholder_vectors: np.ndarray) -> np.ndarray:
    n_stakeholders, n_dims = stakeholder_vectors.shape
    if n_stakeholders < 2:
        return np.zeros(n_dims, dtype=float)

    pair_diffs = [
        np.abs(stakeholder_vectors[i] - stakeholder_vectors[j])
        for i, j in combinations(range(n_stakeholders), 2)
    ]
    return np.mean(np.vstack(pair_diffs), axis=0)


def build_harm_assessment(
    *,
    dimension_scores: dict[str, float],
    stakeholder_weights: dict[str, dict[str, float]],
    framework_weights: dict[str, float],
) -> HarmAssessment:
    ordered_scores = np.array(
        [float(dimension_scores[dimension]) for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    normalized_scores = np.array(
        [normalize_likert(value) for value in ordered_scores],
        dtype=float,
    )
    base_risk = np.clip(1.0 - normalized_scores, 0.0, 1.0)

    stakeholder_matrix = np.vstack(
        [
            np.array(
                [float(weights[dimension]) for dimension in UNIFIED_DIMENSIONS],
                dtype=float,
            )
            for _, weights in sorted(stakeholder_weights.items())
        ]
    )
    disagreement = _mean_pairwise_abs_diff(stakeholder_matrix)
    harm_vector = np.clip(
        (_ALPHA_BASE_RISK * base_risk) + (_BETA_DISAGREEMENT * disagreement),
        0.0,
        1.0,
    )

    framework_vector = np.array(
        [float(framework_weights[dimension]) for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    framework_sum = float(np.sum(framework_vector))
    if framework_sum <= 0.0 or not np.isfinite(framework_sum):
        framework_vector = np.full(len(UNIFIED_DIMENSIONS), 1.0 / len(UNIFIED_DIMENSIONS), dtype=float)
    else:
        framework_vector = framework_vector / framework_sum

    overall_score = float(np.clip(np.dot(harm_vector, framework_vector), 0.0, 1.0))
    top_indices = np.argsort(-harm_vector, kind="stable")[:2]
    top_risk_domains = [UNIFIED_DIMENSIONS[index] for index in top_indices]

    by_dimension = {
        UNIFIED_DIMENSIONS[index]: float(harm_vector[index])
        for index in range(len(UNIFIED_DIMENSIONS))
    }
    domain_scores: list[HarmDomainScore] = []
    for domain_id, dimension in _HARM_DOMAIN_MAP:
        score = by_dimension[dimension]
        domain_scores.append(
            HarmDomainScore(
                domain_id=domain_id,
                unified_dimension=dimension,
                score=score,
                severity=_severity(score),
                evidence_note=(
                    "Derived from normalized base risk and mean pairwise stakeholder "
                    "weight disagreement."
                ),
            )
        )

    return HarmAssessment(
        overall_score=overall_score,
        overall_severity=_severity(overall_score),
        domain_scores=domain_scores,
        top_risk_domains=top_risk_domains,
        model_version=MODEL_VERSION,
    )
