from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def detect_framework_conflicts(framework_ids: Iterable[str]) -> dict[str, Any]:
    return {
        "framework_ids": sorted(set(framework_ids)),
        "conflicts": [],
        "summary": "No framework conflicts detected (placeholder).",
    }


def detect_stakeholder_conflicts(stakeholder_ids: Iterable[int]) -> dict[str, Any]:
    return {
        "stakeholder_ids": sorted(set(stakeholder_ids)),
        "conflicts": [],
        "summary": "No stakeholder conflicts detected (placeholder).",
    }


def build_conflict_matrix(
    stakeholder_ids: Iterable[int],
    framework_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "stakeholder_ids": sorted(set(stakeholder_ids)),
        "framework_ids": sorted(set(framework_ids)),
        "matrix": [],
    }
