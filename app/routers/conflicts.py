"""
==============================
FEATURE FREEZE NOTICE
==============================
This file is part of the frozen API surface for FYP evaluation.
Do NOT modify request/response schemas or endpoint paths.
Minor bug fixes allowed.
Major changes require version bump and schema hash update.
==============================
"""

from __future__ import annotations

from itertools import combinations
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from scipy.stats import spearmanr as _scipy_spearmanr
except Exception:  # pragma: no cover - fallback for environments without scipy
    _scipy_spearmanr = None

from app.database import get_db
from app.framework_registry import get_framework, get_stakeholder
from app.harm_assessment import build_harm_assessment
from app.models import (
    ConflictLevel,
    ConflictReport,
    ConflictRequest,
    ErrorResponse,
    LIKERT_MAX,
    LIKERT_MIN,
    StakeholderConflict,
    UNIFIED_DIMENSIONS,
)
from app.scoring_engine import normalize_likert, topsis_score, validate_likert
from app.audit_log import write_audit_record

router = APIRouter(prefix="/api", tags=["Conflict Detection"])

_WEIGHTS_TIE_BREAK_ORDER: tuple[str, ...] = (
    "accountability",
    "privacy_data_governance",
    "fairness_nondiscrimination",
    "transparency_explainability",
    "safety_robustness",
    "human_agency_oversight",
)
_WEIGHTS_TIE_BREAK_INDEX = {
    dimension: index
    for index, dimension in enumerate(_WEIGHTS_TIE_BREAK_ORDER)
}


def _resolve_framework_id(payload: ConflictRequest) -> str:
    framework_id = payload.framework_id
    if framework_id:
        return framework_id
    if payload.framework_ids:
        return payload.framework_ids[0]
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Either framework_id or framework_ids[0] must be provided.",
    )


def _extract_dimension_scores(payload: ConflictRequest) -> np.ndarray:
    if payload.ai_system is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ai_system is required for conflict analysis.",
        )

    raw_scores = payload.ai_system.context.get("dimension_scores")
    if not isinstance(raw_scores, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ai_system.context.dimension_scores is required with all unified dimensions.",
        )

    ordered_scores: list[float] = []
    for dimension in UNIFIED_DIMENSIONS:
        if dimension not in raw_scores:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing ai_system.context.dimension_scores['{dimension}'].",
            )
        try:
            score = float(raw_scores[dimension])
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid score for '{dimension}'. "
                    f"Must be a number in [{LIKERT_MIN}, {LIKERT_MAX}]."
                ),
            ) from exc
        try:
            validate_likert(score, LIKERT_MIN, LIKERT_MAX)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Score for '{dimension}' must be between {LIKERT_MIN} and {LIKERT_MAX}.",
            ) from exc
        ordered_scores.append(score)

    return np.asarray(ordered_scores, dtype=float)


def _ordered_criteria_types(framework_id: str, framework_dimensions: list) -> list[str]:
    dimension_map = {dimension.name: dimension for dimension in framework_dimensions}
    missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in dimension_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Framework '{framework_id}' is missing criteria types for dimensions: "
                + ", ".join(missing)
            ),
        )

    criteria_types: list[str] = []
    for dimension in UNIFIED_DIMENSIONS:
        raw_type = getattr(dimension_map[dimension].criteria_type, "value", dimension_map[dimension].criteria_type)
        criteria_type = str(raw_type).strip().lower()
        if criteria_type not in {"benefit", "cost"}:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Framework '{framework_id}' has invalid criteria type '{criteria_type}'.",
            )
        criteria_types.append(criteria_type)

    return criteria_types


def _validate_weights(weights: dict[str, float], stakeholder_id: str) -> dict[str, float]:
    if not isinstance(weights, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weights for stakeholder '{stakeholder_id}' must be an object.",
        )

    missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in weights]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Weights for stakeholder '{stakeholder_id}' are missing dimensions: "
                + ", ".join(missing)
            ),
        )

    normalized: dict[str, float] = {}
    for dimension in UNIFIED_DIMENSIONS:
        raw_value = weights.get(dimension)
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid weight for '{dimension}' in stakeholder '{stakeholder_id}'.",
            ) from exc
        if value < 0.0 or value > 1.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Weight for '{dimension}' in stakeholder '{stakeholder_id}' must be in [0, 1].",
            )
        normalized[dimension] = value

    total = sum(normalized.values())
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Weights for stakeholder '{stakeholder_id}' must sum to 1.0 (±0.01); got {total:.4f}."
            ),
        )

    return normalized


def _conflict_level_from_rho(rho: float) -> ConflictLevel:
    if rho > 0.7:
        return ConflictLevel.LOW
    if rho > 0.3:
        return ConflictLevel.MODERATE
    return ConflictLevel.HIGH


def _ranking_to_positions(ranking: list[str]) -> dict[str, int]:
    return {dimension: index for index, dimension in enumerate(ranking)}


def _spearman_rho(rank_vector_a: np.ndarray, rank_vector_b: np.ndarray) -> float:
    if _scipy_spearmanr is not None:
        rho, _ = _scipy_spearmanr(rank_vector_a, rank_vector_b)
        return float(rho) if np.isfinite(rho) else 0.0

    centered_a = rank_vector_a - float(np.mean(rank_vector_a))
    centered_b = rank_vector_b - float(np.mean(rank_vector_b))
    denominator = float(np.linalg.norm(centered_a) * np.linalg.norm(centered_b))
    if denominator == 0.0:
        return 0.0
    rho = float(np.dot(centered_a, centered_b) / denominator)
    return float(np.clip(rho, -1.0, 1.0))


@router.post(
    "/conflicts",
    response_model=ConflictReport,
    responses={404: {"model": ErrorResponse}},
)
def analyze_conflicts(
    payload: ConflictRequest,
    db: Session = Depends(get_db),
) -> ConflictReport:
    run_id = str(uuid4())

    framework_id = _resolve_framework_id(payload)
    framework = get_framework(framework_id)
    if framework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Framework '{framework_id}' not found.",
        )

    decision_vector = _extract_dimension_scores(payload)
    decision_matrix = decision_vector.reshape(1, len(UNIFIED_DIMENSIONS))
    normalized_scores = np.array(
        [normalize_likert(score, LIKERT_MIN, LIKERT_MAX) for score in decision_vector],
        dtype=float,
    )

    criteria_types = _ordered_criteria_types(framework.id, framework.dimensions)

    stakeholder_rankings_contrib: dict[str, list[str]] = {}
    stakeholder_rankings_weights: dict[str, list[str]] = {}
    stakeholder_scores: dict[str, float] = {}
    correlation_matrix_contrib: dict[str, dict[str, float]] = {
        stakeholder_id: {
            other_id: (1.0 if stakeholder_id == other_id else 0.0)
            for other_id in payload.stakeholder_ids
        }
        for stakeholder_id in payload.stakeholder_ids
    }
    correlation_matrix_weights: dict[str, dict[str, float]] = {
        stakeholder_id: {
            other_id: (1.0 if stakeholder_id == other_id else 0.0)
            for other_id in payload.stakeholder_ids
        }
        for stakeholder_id in payload.stakeholder_ids
    }
    pairwise_rho_weights: dict[str, float] = {}
    resolved_weight_vectors: dict[str, dict[str, float]] = {}

    for stakeholder_id in payload.stakeholder_ids:
        stakeholder = get_stakeholder(stakeholder_id, db)
        if stakeholder is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stakeholder '{stakeholder_id}' not found.",
            )

        requested_weights = payload.weights.get(stakeholder_id) if payload.weights else None
        stakeholder_weights = _validate_weights(
            requested_weights if requested_weights is not None else stakeholder.weights,
            stakeholder_id,
        )
        resolved_weight_vectors[stakeholder_id] = stakeholder_weights
        weight_vector = np.asarray(
            [stakeholder_weights[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )

        topsis_matrix = np.vstack(
            [
                decision_matrix,
                np.full((1, len(UNIFIED_DIMENSIONS)), LIKERT_MAX, dtype=float),
                np.full((1, len(UNIFIED_DIMENSIONS)), LIKERT_MIN, dtype=float),
            ]
        )
        try:
            stakeholder_scores[stakeholder_id] = float(
                topsis_score(
                    decision_matrix=topsis_matrix,
                    weights=weight_vector,
                    criteria_types=criteria_types,
                    scale_min=LIKERT_MIN,
                    scale_max=LIKERT_MAX,
                )[0]
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid scoring inputs for stakeholder '{stakeholder_id}': {exc}",
            ) from exc

        contributions = np.clip(normalized_scores * weight_vector, 0.0, 1.0)
        ranking_contrib_indices = np.argsort(-contributions, kind="stable")
        stakeholder_rankings_contrib[stakeholder_id] = [
            UNIFIED_DIMENSIONS[index]
            for index in ranking_contrib_indices
        ]
        stakeholder_rankings_weights[stakeholder_id] = sorted(
            UNIFIED_DIMENSIONS,
            key=lambda dimension: (
                -float(stakeholder_weights[dimension]),
                _WEIGHTS_TIE_BREAK_INDEX[dimension],
            ),
        )

    conflicts: list[StakeholderConflict] = []
    for stakeholder_a, stakeholder_b in combinations(payload.stakeholder_ids, 2):
        ranking_contrib_a = stakeholder_rankings_contrib[stakeholder_a]
        ranking_contrib_b = stakeholder_rankings_contrib[stakeholder_b]

        positions_contrib_a = _ranking_to_positions(ranking_contrib_a)
        positions_contrib_b = _ranking_to_positions(ranking_contrib_b)

        rank_vector_contrib_a = np.asarray(
            [positions_contrib_a[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )
        rank_vector_contrib_b = np.asarray(
            [positions_contrib_b[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )

        rho_value = _spearman_rho(rank_vector_contrib_a, rank_vector_contrib_b)

        correlation_matrix_contrib[stakeholder_a][stakeholder_b] = rho_value
        correlation_matrix_contrib[stakeholder_b][stakeholder_a] = rho_value

        ranking_weights_a = stakeholder_rankings_weights[stakeholder_a]
        ranking_weights_b = stakeholder_rankings_weights[stakeholder_b]
        positions_weights_a = _ranking_to_positions(ranking_weights_a)
        positions_weights_b = _ranking_to_positions(ranking_weights_b)
        rank_vector_weights_a = np.asarray(
            [positions_weights_a[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )
        rank_vector_weights_b = np.asarray(
            [positions_weights_b[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )
        rho_weights = _spearman_rho(rank_vector_weights_a, rank_vector_weights_b)
        correlation_matrix_weights[stakeholder_a][stakeholder_b] = rho_weights
        correlation_matrix_weights[stakeholder_b][stakeholder_a] = rho_weights
        pair_key = "|".join(sorted((stakeholder_a, stakeholder_b)))
        pairwise_rho_weights[pair_key] = rho_weights

        rank_differences = {
            dimension: abs(positions_contrib_a[dimension] - positions_contrib_b[dimension])
            for dimension in UNIFIED_DIMENSIONS
        }
        conflicting_dimensions = sorted(
            UNIFIED_DIMENSIONS,
            key=lambda dimension: (-rank_differences[dimension], dimension),
        )[:2]

        conflicts.append(
            StakeholderConflict(
                stakeholder_a_id=stakeholder_a,
                stakeholder_b_id=stakeholder_b,
                conflict_level=_conflict_level_from_rho(rho_value),
                spearman_rho=rho_value,
                conflicting_dimensions=conflicting_dimensions,
            )
        )

    mean_rho = float(np.mean([conflict.spearman_rho for conflict in conflicts])) if conflicts else 1.0
    overall_conflict = _conflict_level_from_rho(mean_rho).value
    framework_weights = {
        dimension.name: float(dimension.weight_default)
        for dimension in framework.dimensions
    }
    harm_assessment = build_harm_assessment(
        dimension_scores={
            dimension: float(decision_vector[index])
            for index, dimension in enumerate(UNIFIED_DIMENSIONS)
        },
        stakeholder_weights=resolved_weight_vectors,
        framework_weights=framework_weights,
    )

    result = ConflictReport(
        summary=(
            f"Conflict analysis for framework '{framework.id}' indicates "
            f"{overall_conflict} overall stakeholder disagreement."
        ),
        conflicts=conflicts,
        pareto_solutions=[],
        metadata={
            "framework_id": framework.id,
            "stakeholder_rankings": stakeholder_rankings_contrib,
            "stakeholder_rankings_contrib": stakeholder_rankings_contrib,
            "stakeholder_rankings_weights": stakeholder_rankings_weights,
            "correlation_matrix": correlation_matrix_contrib,
            "correlation_matrix_contrib": correlation_matrix_contrib,
            "correlation_matrix_weights": correlation_matrix_weights,
            "pairwise_rho_weights": pairwise_rho_weights,
            "ai_system_id": payload.ai_system.id if payload.ai_system else None,
            "ai_system_name": payload.ai_system.name if payload.ai_system else None,
            "scoring_method": "topsis",
            "stakeholder_scores": stakeholder_scores,
            "run_id": run_id,
        },
        harm_assessment=harm_assessment,
    )

    write_audit_record(
        run_id=run_id,
        endpoint_path="/api/conflicts",
        method="POST",
        request_body=payload.model_dump(mode="json"),
        response_body=result.model_dump(mode="json"),
        status_code=200,
    )

    return result
