from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medf.db")

DEFAULT_STAKEHOLDERS = (
    {
        "name": "Developer",
        "role": "Builder",
        "description": "Represents the AI system developers and maintainers.",
    },
    {
        "name": "Regulator",
        "role": "Oversight",
        "description": "Represents legal, policy, and compliance stakeholders.",
    },
    {
        "name": "Affected Community",
        "role": "Impact",
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

    target_names = [item["name"] for item in DEFAULT_STAKEHOLDERS]
    existing_names = {
        name
        for (name,) in db.query(StakeholderORM.name)
        .filter(StakeholderORM.name.in_(target_names))
        .all()
    }

    inserted = 0
    for stakeholder in DEFAULT_STAKEHOLDERS:
        if stakeholder["name"] in existing_names:
            continue
        db.add(StakeholderORM(**stakeholder))
        inserted += 1

    if inserted:
        db.commit()

    return inserted
