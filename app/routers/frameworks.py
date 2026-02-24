from fastapi import APIRouter

from app.framework_registry import list_frameworks
from app.models import FrameworkSummary

router = APIRouter(prefix="/frameworks", tags=["frameworks"])


@router.get("", response_model=list[FrameworkSummary])
def get_frameworks() -> list[FrameworkSummary]:
    return list_frameworks()
