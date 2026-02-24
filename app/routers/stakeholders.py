from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Stakeholder, StakeholderORM

router = APIRouter(prefix="/stakeholders", tags=["stakeholders"])


@router.get("/", response_model=list[Stakeholder])
def get_stakeholders(db: Session = Depends(get_db)) -> list[StakeholderORM]:
    return db.query(StakeholderORM).order_by(StakeholderORM.id.asc()).all()
