from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Stakeholder, StakeholderORM

router = APIRouter(prefix="/stakeholders", tags=["stakeholders"])


def _to_stakeholder_id(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


@router.get("", response_model=list[Stakeholder])
def get_stakeholders(db: Session = Depends(get_db)) -> list[Stakeholder]:
    records = db.query(StakeholderORM).order_by(StakeholderORM.id.asc()).all()
    return [
        Stakeholder(
            id=_to_stakeholder_id(record.name),
            name=record.name,
            role=record.role,
            description=record.description,
        )
        for record in records
    ]
