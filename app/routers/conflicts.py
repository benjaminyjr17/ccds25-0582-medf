from __future__ import annotations

from itertools import combinations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from scipy.stats import spearmanr as _scipy_spearmanr
except Exception:  # pragma: no cover - fallback for environments without scipy
    _scipy_spearmanr = None

from app.database import get_db
from app.framework_registry import get_framework, get_stakeholder
from app.models import (
    ConflictLevel,
    ConflictReport,
    ConflictRequest,
    ErrorResponse,
    StakeholderConflict,
    UNIFIED_DIMENSIONS,
)
from app.scoring_engine import topsis_score

router = APIRouter(prefix="/api", tags=["Conflict Detection"])


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
                detail=f"Invalid score for '{dimension}'.",
            ) from exc
        if score < 1.0 or score > 5.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Score for '{dimension}' must be between 1 and 5.",
            )
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
    framework_id = _resolve_framework_id(payload)
    framework = get_framework(framework_id)
    if framework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Framework '{framework_id}' not found.",
        )

    decision_vector = _extract_dimension_scores(payload)
    decision_matrix = decision_vector.reshape(1, len(UNIFIED_DIMENSIONS))
    normalized_scores = np.clip((decision_vector - 1.0) / 4.0, 0.0, 1.0)

    criteria_types = _ordered_criteria_types(framework.id, framework.dimensions)

    stakeholder_rankings: dict[str, list[str]] = {}
    stakeholder_scores: dict[str, float] = {}
    correlation_matrix: dict[str, dict[str, float]] = {
        stakeholder_id: {
            other_id: (1.0 if stakeholder_id == other_id else 0.0)
            for other_id in payload.stakeholder_ids
        }
        for stakeholder_id in payload.stakeholder_ids
    }

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
        weight_vector = np.asarray(
            [stakeholder_weights[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )

        topsis_matrix = np.vstack(
            [
                decision_matrix,
                np.full((1, len(UNIFIED_DIMENSIONS)), 5.0, dtype=float),
                np.full((1, len(UNIFIED_DIMENSIONS)), 1.0, dtype=float),
            ]
        )
        try:
            stakeholder_scores[stakeholder_id] = float(
                topsis_score(
                    decision_matrix=topsis_matrix,
                    weights=weight_vector,
                    criteria_types=criteria_types,
                )[0]
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid scoring inputs for stakeholder '{stakeholder_id}': {exc}",
            ) from exc

        contributions = np.clip(normalized_scores * weight_vector, 0.0, 1.0)
        ranking_indices = np.argsort(-contributions, kind="stable")
        stakeholder_rankings[stakeholder_id] = [
            UNIFIED_DIMENSIONS[index]
            for index in ranking_indices
        ]

    conflicts: list[StakeholderConflict] = []
    for stakeholder_a, stakeholder_b in combinations(payload.stakeholder_ids, 2):
        ranking_a = stakeholder_rankings[stakeholder_a]
        ranking_b = stakeholder_rankings[stakeholder_b]

        positions_a = _ranking_to_positions(ranking_a)
        positions_b = _ranking_to_positions(ranking_b)

        rank_vector_a = np.asarray(
            [positions_a[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )
        rank_vector_b = np.asarray(
            [positions_b[dimension] for dimension in UNIFIED_DIMENSIONS],
            dtype=float,
        )

        rho_value = _spearman_rho(rank_vector_a, rank_vector_b)

        correlation_matrix[stakeholder_a][stakeholder_b] = rho_value
        correlation_matrix[stakeholder_b][stakeholder_a] = rho_value

        rank_differences = {
            dimension: abs(positions_a[dimension] - positions_b[dimension])
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

    return ConflictReport(
        summary=(
            f"Conflict analysis for framework '{framework.id}' indicates "
            f"{overall_conflict} overall stakeholder disagreement."
        ),
        conflicts=conflicts,
        pareto_solutions=[],
        metadata={
            "framework_id": framework.id,
            "stakeholder_rankings": stakeholder_rankings,
            "correlation_matrix": correlation_matrix,
            "ai_system_id": payload.ai_system.id if payload.ai_system else None,
            "ai_system_name": payload.ai_system.name if payload.ai_system else None,
            "scoring_method": "topsis",
            "stakeholder_scores": stakeholder_scores,
        },
    )
