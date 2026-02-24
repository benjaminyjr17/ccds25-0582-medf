from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DBStakeholderProfile,
    ErrorResponse,
    StakeholderCreateRequest,
    StakeholderProfile,
    StakeholderRole,
)

router = APIRouter(prefix="/api", tags=["Stakeholders"])


def _to_profile(row: DBStakeholderProfile) -> StakeholderProfile:
    return StakeholderProfile(
        id=row.id,
        name=row.name,
        role=StakeholderRole(row.role),
        description=row.description,
        weights=row.weights,
        is_default=row.is_default,
        created_at=row.created_at,
    )


@router.get("/stakeholders", response_model=list[StakeholderProfile])
def get_stakeholders(db: Session = Depends(get_db)) -> list[StakeholderProfile]:
    rows = (
        db.query(DBStakeholderProfile)
        .order_by(DBStakeholderProfile.is_default.desc(), DBStakeholderProfile.created_at.asc())
        .all()
    )
    return [_to_profile(row) for row in rows]


@router.post(
    "/stakeholders",
    response_model=StakeholderProfile,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def create_stakeholder(
    payload: StakeholderCreateRequest,
    db: Session = Depends(get_db),
) -> StakeholderProfile:
    existing = db.query(DBStakeholderProfile).filter(DBStakeholderProfile.name == payload.name).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stakeholder with name '{payload.name}' already exists.",
        )

    row = DBStakeholderProfile(
        id=f"custom_{uuid4().hex[:8]}",
        name=payload.name,
        role=StakeholderRole.CUSTOM.value,
        description=payload.description,
        is_default=False,
    )
    row.weights = payload.weights

    db.add(row)
    db.commit()
    db.refresh(row)

    return _to_profile(row)
