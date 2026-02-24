from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.models import ParetoSolution


def compute_pairwise_spearman(ranking_a: list[str], ranking_b: list[str]) -> tuple[float, float]:
    _ = (ranking_a, ranking_b)
    return 0.0, 1.0


def find_divergent_dimensions(
    dimension_scores_a: dict[str, float],
    dimension_scores_b: dict[str, float],
    threshold: float = 0.25,
) -> list[str]:
    _ = (dimension_scores_a, dimension_scores_b, threshold)
    return []


def find_pareto_solutions(
    stakeholder_scores: list[dict[str, float]] | None = None,
    candidate_weights: list[dict[str, dict[str, float]]] | None = None,
) -> list[ParetoSolution]:
    _ = (stakeholder_scores, candidate_weights)
    return []


def detect_framework_conflicts(framework_ids: Iterable[str]) -> dict[str, Any]:
    return {
        "framework_ids": sorted(set(framework_ids)),
        "conflicts": [],
        "summary": "No framework conflicts detected (placeholder).",
    }


def detect_stakeholder_conflicts(stakeholder_ids: Iterable[str]) -> dict[str, Any]:
    return {
        "stakeholder_ids": sorted(set(stakeholder_ids)),
        "conflicts": [],
        "summary": "No stakeholder conflicts detected (placeholder).",
    }


def build_conflict_matrix(
    stakeholder_ids: Iterable[str],
    framework_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "stakeholder_ids": sorted(set(stakeholder_ids)),
        "framework_ids": sorted(set(framework_ids)),
        "matrix": [],
    }
