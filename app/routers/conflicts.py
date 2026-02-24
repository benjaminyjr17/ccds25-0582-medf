from fastapi import APIRouter

from app.conflict_detection import (
    build_conflict_matrix,
    detect_framework_conflicts,
    detect_stakeholder_conflicts,
)
from app.models import ConflictCheckRequest, ConflictCheckResponse

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.post("", response_model=ConflictCheckResponse)
def analyze_conflicts(payload: ConflictCheckRequest) -> ConflictCheckResponse:
    framework_conflicts = detect_framework_conflicts(payload.framework_ids)
    stakeholder_conflicts = detect_stakeholder_conflicts(payload.stakeholder_ids)
    matrix = build_conflict_matrix(payload.stakeholder_ids, payload.framework_ids)

    return ConflictCheckResponse(
        summary="Conflict analysis is currently a placeholder.",
        conflicts=[],
        metadata={
            "frameworks": framework_conflicts,
            "stakeholders": stakeholder_conflicts,
            "matrix": matrix,
        },
    )
