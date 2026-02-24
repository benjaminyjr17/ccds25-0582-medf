from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.database import SessionLocal, init_db
from app.framework_registry import (
    get_all_frameworks,
    load_frameworks,
    seed_default_stakeholders,
)
from app.models import DBStakeholderProfile
from app.routers.frameworks import router as frameworks_router
from app.routers.stakeholders import router as stakeholders_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    load_frameworks()
    seed_default_stakeholders()
    yield


app = FastAPI(
    title="MEDF API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(stakeholders_router)
app.include_router(frameworks_router)


@app.get("/api/health", tags=["Health"])
def health() -> dict[str, Any]:
    frameworks_loaded = len(get_all_frameworks())
    with SessionLocal() as db:
        stakeholder_profiles_loaded = db.query(DBStakeholderProfile).count()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "frameworks_loaded": frameworks_loaded,
        "stakeholder_profiles_loaded": stakeholder_profiles_loaded,
    }
