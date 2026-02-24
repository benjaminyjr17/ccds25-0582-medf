from __future__ import annotations

from itertools import combinations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.conflict_detection import (
    compute_pairwise_spearman,
    find_divergent_dimensions,
    find_pareto_solutions,
)
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
from app.scoring_engine import compute_scores

router = APIRouter(prefix="/api", tags=["Conflict Detection"])


def _placeholder_dimension_scores(framework_id: str, stakeholder_id: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for index, dimension in enumerate(UNIFIED_DIMENSIONS, start=1):
        seed = sum(ord(char) for char in f"{framework_id}:{stakeholder_id}:{dimension}") + (index * 11)
        scores[dimension] = float((seed % 5) + 1)
    return scores


def _conflict_level_from_rho(rho: float) -> ConflictLevel:
    absolute_rho = abs(rho)
    if absolute_rho >= 0.8:
        return ConflictLevel.LOW
    if absolute_rho >= 0.5:
        return ConflictLevel.MODERATE
    return ConflictLevel.HIGH


@router.post(
    "/conflicts",
    response_model=ConflictReport,
    responses={404: {"model": ErrorResponse}},
)
def analyze_conflicts(
    payload: ConflictRequest,
    db: Session = Depends(get_db),
) -> ConflictReport:
    for framework_id in payload.framework_ids:
        if get_framework(framework_id) is None:
            error = ErrorResponse(
                detail=f"Framework '{framework_id}' not found.",
                error_code="framework_not_found",
                path=f"/api/conflicts/{framework_id}",
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.model_dump())

    stakeholder_weights: dict[str, dict[str, float]] = {}
    for stakeholder_id in payload.stakeholder_ids:
        stakeholder = get_stakeholder(stakeholder_id, db)
        if stakeholder is None:
            error = ErrorResponse(
                detail=f"Stakeholder '{stakeholder_id}' not found.",
                error_code="stakeholder_not_found",
                path=f"/api/conflicts/{stakeholder_id}",
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.model_dump())
        stakeholder_weights[stakeholder_id] = stakeholder.weights

    rankings: dict[str, list[str]] = {}
    dimension_profiles: dict[str, dict[str, float]] = {}

    for stakeholder_id, weights in stakeholder_weights.items():
        framework_scores: list[tuple[str, float]] = []
        profile = {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}

        for framework_id in payload.framework_ids:
            scored = compute_scores(
                _placeholder_dimension_scores(framework_id, stakeholder_id),
                weights,
                method="topsis",
            )
            framework_scores.append((framework_id, float(scored["overall_score"])))

            per_dimension = scored["dimension_scores"]
            for dimension in UNIFIED_DIMENSIONS:
                profile[dimension] += float(per_dimension.get(dimension, 0.0))

        count = len(payload.framework_ids) if payload.framework_ids else 1
        dimension_profiles[stakeholder_id] = {
            dimension: profile[dimension] / count
            for dimension in UNIFIED_DIMENSIONS
        }
        rankings[stakeholder_id] = [
            framework_id
            for framework_id, _ in sorted(framework_scores, key=lambda item: item[1], reverse=True)
        ]

    conflicts: list[StakeholderConflict] = []
    for stakeholder_a, stakeholder_b in combinations(payload.stakeholder_ids, 2):
        rho, _ = compute_pairwise_spearman(rankings[stakeholder_a], rankings[stakeholder_b])
        divergent = find_divergent_dimensions(
            dimension_profiles[stakeholder_a],
            dimension_profiles[stakeholder_b],
        )
        conflicts.append(
            StakeholderConflict(
                stakeholder_a_id=stakeholder_a,
                stakeholder_b_id=stakeholder_b,
                conflict_level=_conflict_level_from_rho(rho),
                spearman_rho=rho,
                conflicting_dimensions=divergent,
            )
        )

    pareto_solutions = find_pareto_solutions()

    return ConflictReport(
        summary="Deterministic Stage 1C placeholder conflict report.",
        conflicts=conflicts,
        pareto_solutions=pareto_solutions,
        metadata={
            "framework_ids": payload.framework_ids,
            "stakeholder_ids": payload.stakeholder_ids,
            "pairwise_conflicts": len(conflicts),
        },
    )
