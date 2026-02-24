from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medf.db")

DEFAULT_STAKEHOLDERS = (
    {
        "name": "Developer",
        "role": "developer",
        "description": "Represents the AI system developers and maintainers.",
    },
    {
        "name": "Regulator",
        "role": "regulator",
        "description": "Represents legal, policy, and compliance stakeholders.",
    },
    {
        "name": "Affected Community",
        "role": "affected_community",
        "description": "Represents individuals and groups impacted by deployment.",
    },
)

_connect_args: dict[str, bool] = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def seed_default_stakeholders(db: Session) -> int:
    from app.models import StakeholderORM

    existing_rows = {
        row.name: row
        for row in db.query(StakeholderORM)
        .filter(StakeholderORM.name.in_([item["name"] for item in DEFAULT_STAKEHOLDERS]))
        .all()
    }

    changed = 0
    for stakeholder in DEFAULT_STAKEHOLDERS:
        existing_row = existing_rows.get(stakeholder["name"])
        if existing_row is None:
            db.add(StakeholderORM(**stakeholder))
            changed += 1
            continue

        if existing_row.role != stakeholder["role"] or existing_row.description != stakeholder["description"]:
            existing_row.role = stakeholder["role"]
            existing_row.description = stakeholder["description"]
            changed += 1

    if changed:
        db.commit()

    return changed
