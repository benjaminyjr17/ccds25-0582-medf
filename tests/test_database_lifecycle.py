from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.database as database
import app.framework_registry as framework_registry
from app.database import Base
from app.models import DBStakeholderProfile, UNIFIED_DIMENSIONS


def _tmp_session_factory(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'lifecycle.db'}",
        connect_args={"check_same_thread": False},
    )
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, session_local


def test_get_db_closes_session_on_generator_close(monkeypatch) -> None:
    class DummySession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    dummy = DummySession()
    monkeypatch.setattr(database, "SessionLocal", lambda: dummy)

    gen = database.get_db()
    yielded = next(gen)
    assert yielded is dummy
    assert dummy.closed is False

    gen.close()
    assert dummy.closed is True


def test_init_db_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'init-idempotent.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", engine)

    database.init_db()
    database.init_db()

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    table_names = {str(row[0]) for row in rows}
    assert "stakeholder_profiles" in table_names


def test_seed_default_stakeholders_is_idempotent_and_overwrites_defaults(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _, temp_session_local = _tmp_session_factory(tmp_path)
    monkeypatch.setattr(framework_registry, "SessionLocal", temp_session_local)

    altered_developer = DBStakeholderProfile(
        id="developer",
        name="Old Developer",
        role="custom",
        description="outdated",
        is_default=False,
    )
    altered_developer.weights = {
        dimension: (1.0 / len(UNIFIED_DIMENSIONS))
        for dimension in UNIFIED_DIMENSIONS
    }

    with temp_session_local() as session:
        session.add(altered_developer)
        session.commit()

    framework_registry.seed_default_stakeholders()
    framework_registry.seed_default_stakeholders()

    expected_default_ids = {
        "developer",
        "regulator",
        "affected_community",
    }

    with temp_session_local() as session:
        rows = (
            session.query(DBStakeholderProfile)
            .filter(DBStakeholderProfile.id.in_(expected_default_ids))
            .all()
        )
        assert len(rows) == 3

        by_id = {row.id: row for row in rows}
        developer = by_id["developer"]
        assert developer.name == "Developer"
        assert developer.role == "developer"
        assert developer.is_default is True
        assert developer.weights == framework_registry._DEFAULT_STAKEHOLDER_WEIGHTS["developer"]

        for expected_id in expected_default_ids:
            count = (
                session.query(DBStakeholderProfile)
                .filter(DBStakeholderProfile.id == expected_id)
                .count()
            )
            assert count == 1
