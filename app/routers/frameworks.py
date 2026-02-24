from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.framework_registry import get_all_frameworks, get_framework
from app.models import EthicalFramework

router = APIRouter(prefix="/api", tags=["Frameworks"])


@router.get("/frameworks", response_model=list[EthicalFramework])
def list_frameworks() -> list[EthicalFramework]:
    return get_all_frameworks()


@router.get(
    "/frameworks/{framework_id}",
    response_model=EthicalFramework,
)
def get_framework_by_id(framework_id: str) -> EthicalFramework:
    framework = get_framework(framework_id)
    if framework is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Framework '{framework_id}' not found",
        )
    return framework
