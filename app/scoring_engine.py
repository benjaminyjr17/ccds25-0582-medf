from __future__ import annotations

from collections.abc import Iterable

from app.models import EvaluationRequest, FrameworkScore


def compute_scores(
    request: EvaluationRequest,
    framework_ids: Iterable[str] | None = None,
) -> list[FrameworkScore]:
    candidate_ids = request.framework_ids or list(framework_ids or [])
    ordered_ids = sorted(set(candidate_ids))

    scores: list[FrameworkScore] = []
    for index, framework_id in enumerate(ordered_ids, start=1):
        raw_value = sum(ord(ch) for ch in framework_id) + (index * 17)
        score = round((raw_value % 100) / 100.0, 3)
        scores.append(FrameworkScore(framework_id=framework_id, score=score))
    return scores
