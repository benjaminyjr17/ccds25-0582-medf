from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.framework_registry import get_framework, get_stakeholder
from app.models import (
    ErrorResponse,
    EvaluateRequest,
    EvaluationResult,
    FrameworkScore,
    RiskLevel,
    ScoringMethod,
    UNIFIED_DIMENSIONS,
)
from app.scoring_engine import compute_scores

router = APIRouter(prefix="/api", tags=["Evaluation"])


def _placeholder_dimension_scores(framework_id: str, ai_system_id: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for index, dimension in enumerate(UNIFIED_DIMENSIONS, start=1):
        seed = sum(ord(char) for char in f"{framework_id}:{ai_system_id}:{dimension}") + (index * 17)
        scores[dimension] = float((seed % 5) + 1)
    return scores


def _risk_level(overall_score: float) -> RiskLevel:
    if overall_score >= 0.8:
        return RiskLevel.LOW
    if overall_score >= 0.6:
        return RiskLevel.MEDIUM
    if overall_score >= 0.4:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


@router.post(
    "/evaluate",
    response_model=EvaluationResult,
    responses={404: {"model": ErrorResponse}},
)
def evaluate(
    payload: EvaluateRequest,
    db: Session = Depends(get_db),
) -> EvaluationResult:
    framework_scores: list[FrameworkScore] = []
    framework_overall_scores: list[float] = []

    for framework_id in payload.framework_ids:
        framework = get_framework(framework_id)
        if framework is None:
            error = ErrorResponse(
                detail=f"Framework '{framework_id}' not found.",
                error_code="framework_not_found",
                path=f"/api/evaluate/{framework_id}",
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.model_dump())

        stakeholder_results: list[float] = []
        aggregated_dimension_scores: dict[str, float] = {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}

        for stakeholder_id in payload.stakeholder_ids:
            stakeholder = get_stakeholder(stakeholder_id, db)
            if stakeholder is None:
                error = ErrorResponse(
                    detail=f"Stakeholder '{stakeholder_id}' not found.",
                    error_code="stakeholder_not_found",
                    path=f"/api/evaluate/{stakeholder_id}",
                )
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.model_dump())

            weights = payload.weights.get(stakeholder_id) or stakeholder.weights
            raw_dimension_scores = _placeholder_dimension_scores(framework.id, payload.ai_system.id)
            scored = compute_scores(raw_dimension_scores, weights, payload.scoring_method.value)

            stakeholder_results.append(float(scored["overall_score"]))
            per_dimension = scored["dimension_scores"]
            for dimension in UNIFIED_DIMENSIONS:
                aggregated_dimension_scores[dimension] += float(per_dimension.get(dimension, 0.0))

        divisor = len(stakeholder_results) if stakeholder_results else 1
        average_framework_score = sum(stakeholder_results) / divisor if stakeholder_results else 0.0
        average_dimension_scores = {
            dimension: (aggregated_dimension_scores[dimension] / divisor)
            for dimension in UNIFIED_DIMENSIONS
        }

        framework_overall_scores.append(average_framework_score)
        framework_scores.append(
            FrameworkScore(
                framework_id=framework.id,
                score=average_framework_score,
                dimension_scores=average_dimension_scores,
                risk_level=_risk_level(average_framework_score),
            )
        )

    overall_score = (
        sum(framework_overall_scores) / len(framework_overall_scores)
        if framework_overall_scores
        else 0.0
    )

    return EvaluationResult(
        ai_system_id=payload.ai_system.id,
        scoring_method=ScoringMethod(payload.scoring_method.value),
        framework_scores=framework_scores,
        overall_score=overall_score,
        notes="Deterministic Stage 1C placeholder evaluation.",
    )
