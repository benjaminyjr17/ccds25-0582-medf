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
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    from pymoo.termination import get_termination

    _HAS_PYMOO = True
except Exception:  # pragma: no cover - deterministic fallback if pymoo is unavailable
    NSGA2 = None
    Problem = object
    minimize = None
    get_termination = None
    _HAS_PYMOO = False

from app.database import get_db
from app.framework_registry import get_framework, get_stakeholder
from app.models import (
    AISystemInput,
    ConflictReport,
    ErrorResponse,
    ParetoSolution,
    UNIFIED_DIMENSIONS,
)

router = APIRouter(prefix="/api", tags=["Pareto"])


def _resolve_framework_id_or_422(payload: "ParetoRequest") -> str:
    framework_id = payload.framework_id
    if framework_id:
        return framework_id
    if payload.framework_ids and len(payload.framework_ids) > 0:
        return payload.framework_ids[0]
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Either framework_id or framework_ids[0] must be provided.",
    )


def _extract_x_normalized_or_422(ai_system: AISystemInput) -> np.ndarray:
    raw_scores = ai_system.context.get("dimension_scores")
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

    likert = np.asarray(ordered_scores, dtype=float)
    return np.clip((likert - 1.0) / 4.0, 0.0, 1.0)


def _validate_weight_vector_or_422(raw_weights: dict[str, float], stakeholder_id: str) -> dict[str, float]:
    if not isinstance(raw_weights, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weights for stakeholder '{stakeholder_id}' must be a key/value object.",
        )

    missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in raw_weights]
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
        raw_value = raw_weights.get(dimension)
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

    total = float(sum(normalized.values()))
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Weights for stakeholder '{stakeholder_id}' must sum to 1.0 (±0.01); got {total:.4f}."
            ),
        )

    if total <= 1e-12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weights for stakeholder '{stakeholder_id}' sum to zero.",
        )

    return {
        dimension: normalized[dimension] / total
        for dimension in UNIFIED_DIMENSIONS
    }


def _normalize_simplex(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 1:
        total = float(array.sum())
        if total <= 1e-12:
            return np.full(array.shape[0], 1.0 / array.shape[0], dtype=float)
        return array / total

    totals = np.sum(array, axis=1, keepdims=True)
    fallback = np.full(array.shape, 1.0 / array.shape[1], dtype=float)
    return np.divide(array, totals, out=fallback, where=totals > 1e-12)


def _compute_objectives(
    candidates: np.ndarray,
    stakeholder_matrix: np.ndarray,
    salience_vector: np.ndarray,
) -> np.ndarray:
    normalized = _normalize_simplex(candidates)
    n_candidates = normalized.shape[0]
    n_stakeholders = stakeholder_matrix.shape[0]
    objectives = np.zeros((n_candidates, n_stakeholders), dtype=float)

    for idx in range(n_stakeholders):
        stakeholder_weights = stakeholder_matrix[idx]
        objectives[:, idx] = np.sum(
            salience_vector * np.abs(normalized - stakeholder_weights),
            axis=1,
        )

    return objectives


class ParetoRequest(BaseModel):
    ai_system: AISystemInput
    framework_id: str | None = None
    framework_ids: list[str] | None = None
    stakeholder_ids: list[str]
    weights: dict[str, dict[str, float]] | None = None
    n_solutions: int = Field(default=10, ge=1, le=50)
    pop_size: int = Field(default=64, ge=16, le=256)
    n_gen: int = Field(default=80, ge=10, le=300)
    seed: int = 42

    @field_validator("stakeholder_ids")
    @classmethod
    def validate_stakeholder_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        deduped = list(dict.fromkeys(cleaned))
        if len(deduped) < 2:
            raise ValueError("stakeholder_ids must include at least two stakeholders.")
        return deduped

    @field_validator("weights")
    @classmethod
    def validate_optional_weights(
        cls,
        value: dict[str, dict[str, float]] | None,
    ) -> dict[str, dict[str, float]] | None:
        if value is None:
            return None

        normalized: dict[str, dict[str, float]] = {}
        for stakeholder_id, vector in value.items():
            if not isinstance(vector, dict):
                raise ValueError(f"weights['{stakeholder_id}'] must be a key/value object.")

            missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in vector]
            if missing:
                raise ValueError(
                    f"weights['{stakeholder_id}'] is missing dimensions: {', '.join(missing)}"
                )

            parsed: dict[str, float] = {}
            for dimension in UNIFIED_DIMENSIONS:
                try:
                    score = float(vector[dimension])
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"weights['{stakeholder_id}']['{dimension}'] must be numeric."
                    ) from exc
                if score < 0.0 or score > 1.0:
                    raise ValueError(
                        f"weights['{stakeholder_id}']['{dimension}'] must be in [0, 1]."
                    )
                parsed[dimension] = score

            total = float(sum(parsed.values()))
            if abs(total - 1.0) > 0.01:
                raise ValueError(
                    f"weights['{stakeholder_id}'] must sum to 1.0 (±0.01); got {total:.4f}."
                )

            normalized[stakeholder_id] = {
                dimension: parsed[dimension] / total
                for dimension in UNIFIED_DIMENSIONS
            }

        return normalized

    @model_validator(mode="after")
    def validate_framework_and_scores(self) -> "ParetoRequest":
        framework_id = self.framework_id
        if framework_id is None and self.framework_ids:
            framework_id = self.framework_ids[0]
        if not framework_id:
            raise ValueError("Either framework_id or framework_ids[0] must be provided.")

        raw_scores = self.ai_system.context.get("dimension_scores")
        if not isinstance(raw_scores, dict):
            raise ValueError(
                "ai_system.context.dimension_scores is required with all unified dimensions."
            )

        missing = [dimension for dimension in UNIFIED_DIMENSIONS if dimension not in raw_scores]
        if missing:
            raise ValueError(
                "ai_system.context.dimension_scores is missing dimensions: "
                + ", ".join(missing)
            )

        for dimension in UNIFIED_DIMENSIONS:
            try:
                score = float(raw_scores[dimension])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid ai_system.context.dimension_scores value for '{dimension}'."
                ) from exc
            if score < 1.0 or score > 5.0:
                raise ValueError(
                    f"ai_system.context.dimension_scores['{dimension}'] must be between 1 and 5."
                )

        return self


if _HAS_PYMOO:

    class ConsensusWeightProblem(Problem):
        def __init__(
            self,
            stakeholder_matrix: np.ndarray,
            salience_vector: np.ndarray,
        ) -> None:
            super().__init__(
                n_var=len(UNIFIED_DIMENSIONS),
                n_obj=int(stakeholder_matrix.shape[0]),
                xl=0.0,
                xu=1.0,
            )
            self.stakeholder_matrix = stakeholder_matrix
            self.salience_vector = salience_vector

        def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:  # type: ignore[override]
            out["F"] = _compute_objectives(x, self.stakeholder_matrix, self.salience_vector)


@router.post(
    "/pareto",
    response_model=ConflictReport,
    responses={404: {"model": ErrorResponse}},
)
def generate_pareto_solutions(
    payload: ParetoRequest,
    db: Session = Depends(get_db),
) -> ConflictReport:
    framework_id = _resolve_framework_id_or_422(payload)

    framework = get_framework(framework_id)
    if framework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Framework '{framework_id}' not found.",
        )

    x_normalized = _extract_x_normalized_or_422(payload.ai_system)
    x_sum = float(np.sum(x_normalized))
    if x_sum > 1e-12:
        salience_vector = x_normalized / x_sum
    else:
        salience_vector = np.full(len(UNIFIED_DIMENSIONS), 1.0 / len(UNIFIED_DIMENSIONS), dtype=float)

    stakeholder_vectors: list[np.ndarray] = []
    for stakeholder_id in payload.stakeholder_ids:
        stakeholder = get_stakeholder(stakeholder_id, db)
        if stakeholder is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stakeholder '{stakeholder_id}' not found.",
            )

        override_weights = payload.weights.get(stakeholder_id) if payload.weights else None
        source_weights = override_weights if override_weights is not None else stakeholder.weights
        normalized = _validate_weight_vector_or_422(source_weights, stakeholder_id)
        stakeholder_vectors.append(
            np.asarray([normalized[dimension] for dimension in UNIFIED_DIMENSIONS], dtype=float)
        )

    stakeholder_matrix = np.vstack(stakeholder_vectors)

    if _HAS_PYMOO:
        problem = ConsensusWeightProblem(
            stakeholder_matrix=stakeholder_matrix,
            salience_vector=salience_vector,
        )
        algorithm = NSGA2(pop_size=payload.pop_size)
        termination = get_termination("n_gen", payload.n_gen)
        res = minimize(
            problem,
            algorithm,
            termination=termination,
            seed=payload.seed,
            save_history=False,
            verbose=False,
        )

        raw_x = np.asarray(res.X, dtype=float)
        raw_f = np.asarray(res.F, dtype=float)
        if raw_x.ndim == 1:
            raw_x = raw_x.reshape(1, -1)
            raw_f = raw_f.reshape(1, -1)
    else:
        rng = np.random.default_rng(payload.seed)
        n_candidates = max(payload.pop_size * payload.n_gen, payload.n_solutions * 4)
        raw_x = rng.random((n_candidates, len(UNIFIED_DIMENSIONS)), dtype=float)
        raw_f = _compute_objectives(raw_x, stakeholder_matrix, salience_vector)

    normalized_candidates = _normalize_simplex(raw_x)

    deduped: list[tuple[np.ndarray, np.ndarray, float]] = []
    seen_keys: set[tuple[float, ...]] = set()

    for idx in range(normalized_candidates.shape[0]):
        consensus_weights = normalized_candidates[idx]
        dedupe_key = tuple(np.round(consensus_weights, 4).tolist())
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        objective_vector = raw_f[idx]
        utility_wsm = float(np.dot(consensus_weights, x_normalized))
        deduped.append((consensus_weights, objective_vector, utility_wsm))

    deduped.sort(key=lambda item: (float(np.sum(item[1])), -float(item[2])))
    selected = deduped[: payload.n_solutions]

    pareto_solutions: list[ParetoSolution] = []
    ablation_utility_by_solution: dict[str, float] = {}

    for rank, (consensus, objectives, utility_wsm) in enumerate(selected, start=1):
        solution_id = f"ps_{uuid4().hex[:8]}"
        consensus_map = {
            dimension: float(consensus[index])
            for index, dimension in enumerate(UNIFIED_DIMENSIONS)
        }
        objective_scores = {
            stakeholder_id: float(objectives[index])
            for index, stakeholder_id in enumerate(payload.stakeholder_ids)
        }

        pareto_solutions.append(
            ParetoSolution(
                solution_id=solution_id,
                weights={"consensus": consensus_map},
                objective_scores=objective_scores,
                rank=rank,
            )
        )
        ablation_utility_by_solution[solution_id] = utility_wsm

    x_payload = {
        dimension: float(x_normalized[index])
        for index, dimension in enumerate(UNIFIED_DIMENSIONS)
    }
    salience_payload = {
        dimension: float(salience_vector[index])
        for index, dimension in enumerate(UNIFIED_DIMENSIONS)
    }

    return ConflictReport(
        summary=(
            "Pareto consensus weights (NSGA-II) minimizing salience-weighted distance "
            f"under framework {framework.id}."
        ),
        conflicts=[],
        pareto_solutions=pareto_solutions,
        metadata={
            "framework_id": framework.id,
            "ai_system_id": payload.ai_system.id,
            "ai_system_name": payload.ai_system.name,
            "stakeholder_ids": payload.stakeholder_ids,
            "x_normalized": x_payload,
            "salience_vector": salience_payload,
            "objective_definition": "minimize obj_k(w)=sum_i s_i*|w_i - wk_i|",
            "ablation_definition": "utility_wsm(w)=sum_i w_i*x_i (recorded only, not optimized)",
            "ablation_utility_by_solution": ablation_utility_by_solution,
            "pop_size": payload.pop_size,
            "n_gen": payload.n_gen,
            "seed": payload.seed,
            "n_solutions_returned": len(pareto_solutions),
        },
    )
