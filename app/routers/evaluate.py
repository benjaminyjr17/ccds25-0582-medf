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

from uuid import uuid4

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit_log import write_audit_record
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
from app.scoring_engine import topsis_score, wsm_scores

router = APIRouter(prefix="/api", tags=["Evaluation"])


def _get_dimension_scores(payload: EvaluateRequest) -> dict[str, float]:
    context = payload.ai_system.context or {}
    raw_scores = context.get("dimension_scores")
    if not isinstance(raw_scores, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "ai_system.context.dimension_scores is required and must contain all 6 "
                "unified dimensions with Likert scores in [1, 5]."
            ),
        )

    missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in raw_scores]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "ai_system.context.dimension_scores is missing dimensions: "
                + ", ".join(missing)
            ),
        )

    normalized: dict[str, float] = {}
    for dimension in UNIFIED_DIMENSIONS:
        raw_value = raw_scores.get(dimension)
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid dimension score for '{dimension}'. Must be a number in [1, 5].",
            ) from exc

        if value < 1.0 or value > 5.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dimension '{dimension}' score must be in [1, 5].",
            )
        normalized[dimension] = value

    return normalized


def _validate_weights(weights: dict[str, float], stakeholder_id: str) -> dict[str, float]:
    if not isinstance(weights, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weights for stakeholder '{stakeholder_id}' must be a key/value object.",
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
        criteria_raw = getattr(dimension_map[dimension].criteria_type, "value", dimension_map[dimension].criteria_type)
        criteria_type = str(criteria_raw).strip().lower()
        if criteria_type not in {"benefit", "cost"}:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Framework '{framework_id}' has invalid criteria type '{criteria_type}'.",
            )
        criteria_types.append(criteria_type)

    return criteria_types


def _framework_coverage_weights(framework) -> dict[str, float]:
    dimension_map = {dimension.name: dimension for dimension in framework.dimensions}
    missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in dimension_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Framework '{framework.id}' is missing dimensions for coverage weighting: "
                + ", ".join(missing)
            ),
        )

    raw_counts: dict[str, float] = {}
    for dimension in UNIFIED_DIMENSIONS:
        dimension_obj = dimension_map[dimension]
        count_value = None

        assessment_questions = getattr(dimension_obj, "assessment_questions", None)
        if isinstance(assessment_questions, list):
            non_empty_questions = [
                str(question).strip()
                for question in assessment_questions
                if str(question).strip()
            ]
            if non_empty_questions:
                count_value = float(len(non_empty_questions))

        if count_value is None:
            for key in ("criteria", "subcriteria", "items"):
                list_like = getattr(dimension_obj, key, None)
                if isinstance(list_like, list) and len(list_like) > 0:
                    count_value = float(len(list_like))
                    break

        if count_value is None:
            count_value = 1.0

        try:
            count = float(count_value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Framework '{framework.id}' has invalid coverage count for '{dimension}'.",
            ) from exc

        if not np.isfinite(count) or count < 0.0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Framework '{framework.id}' has non-finite or negative coverage count for '{dimension}'.",
            )

        raw_counts[dimension] = count

    total = float(sum(raw_counts.values()))
    if total <= 0.0 or not np.isfinite(total):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Framework '{framework.id}' coverage counts produce invalid normalization sum "
                f"({total:.4f})."
            ),
        )

    return {
        dimension: float(raw_counts[dimension] / total)
        for dimension in UNIFIED_DIMENSIONS
    }


def _effective_weights(ws: dict[str, float], wf: dict[str, float]) -> np.ndarray:
    stakeholder_vector = np.array([ws[dimension] for dimension in UNIFIED_DIMENSIONS], dtype=float)
    framework_vector = np.array([wf[dimension] for dimension in UNIFIED_DIMENSIONS], dtype=float)
    effective_vector = stakeholder_vector * framework_vector
    effective_sum = float(np.sum(effective_vector))
    if effective_sum <= 0.0 or not np.isfinite(effective_sum):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Effective weights are invalid after framework weighting (non-finite or zero sum).",
        )
    effective_vector = effective_vector / effective_sum
    if not np.all(np.isfinite(effective_vector)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Effective weights contain non-finite values after normalization.",
        )
    return effective_vector


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
    run_id = str(uuid4())

    if payload.scoring_method == ScoringMethod.AHP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AHP scoring not supported in /api/evaluate yet",
        )

    dimension_scores = _get_dimension_scores(payload)
    decision_vector = np.array(
        [dimension_scores[dimension] for dimension in UNIFIED_DIMENSIONS],
        dtype=float,
    )
    decision_matrix = decision_vector.reshape(1, len(UNIFIED_DIMENSIONS))
    normalized_vector = np.clip((decision_vector - 1.0) / 4.0, 0.0, 1.0)

    framework_scores: list[FrameworkScore] = []
    framework_overall_scores: list[float] = []

    for framework_id in payload.framework_ids:
        framework = get_framework(framework_id)
        if framework is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Framework '{framework_id}' not found.",
            )

        criteria_types = _ordered_criteria_types(framework.id, framework.dimensions)
        framework_default_weights = _framework_coverage_weights(framework)

        stakeholder_results: list[float] = []
        aggregated_dimension_scores: dict[str, float] = {dimension: 0.0 for dimension in UNIFIED_DIMENSIONS}

        for stakeholder_id in payload.stakeholder_ids:
            stakeholder = get_stakeholder(stakeholder_id, db)
            if stakeholder is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stakeholder '{stakeholder_id}' not found.",
                )

            stakeholder_weights = _validate_weights(
                payload.weights.get(stakeholder_id) or stakeholder.weights,
                stakeholder_id,
            )
            effective_weight_vector = _effective_weights(
                stakeholder_weights,
                framework_default_weights,
            )

            if payload.scoring_method == ScoringMethod.TOPSIS:
                topsis_matrix = np.vstack(
                    [
                        decision_matrix,
                        np.full((1, len(UNIFIED_DIMENSIONS)), 5.0, dtype=float),
                        np.full((1, len(UNIFIED_DIMENSIONS)), 1.0, dtype=float),
                    ]
                )
                try:
                    score_value = float(
                        topsis_score(
                            decision_matrix=topsis_matrix,
                            weights=effective_weight_vector,
                            criteria_types=criteria_types,
                        )[0]
                    )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid TOPSIS input for stakeholder '{stakeholder_id}': {exc}",
                    ) from exc
            elif payload.scoring_method == ScoringMethod.WSM:
                try:
                    score_value = float(
                        wsm_scores(
                            decision_matrix=decision_matrix,
                            weights=effective_weight_vector,
                        )[0]
                    )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid WSM input for stakeholder '{stakeholder_id}': {exc}",
                    ) from exc
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported scoring method '{payload.scoring_method.value}'.",
                )

            stakeholder_results.append(score_value)
            per_dimension_contrib = np.clip(normalized_vector * effective_weight_vector, 0.0, 1.0)
            for dimension in UNIFIED_DIMENSIONS:
                index = UNIFIED_DIMENSIONS.index(dimension)
                aggregated_dimension_scores[dimension] += float(per_dimension_contrib[index])

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

    result = EvaluationResult(
        ai_system_id=payload.ai_system.id,
        scoring_method=ScoringMethod(payload.scoring_method.value),
        framework_scores=framework_scores,
        overall_score=overall_score,
        notes=(
            "Evaluation computed from supplied ai_system.context.dimension_scores. "
            "framework_weighting=coverage_counts(product_pooling). "
            f"run_id={run_id}"
        ),
    )

    write_audit_record(
        run_id=run_id,
        endpoint_path="/api/evaluate",
        method="POST",
        request_body=payload.model_dump(mode="json"),
        response_body=result.model_dump(mode="json"),
        status_code=200,
    )

    return result
