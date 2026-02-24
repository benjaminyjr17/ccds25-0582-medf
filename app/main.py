from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import SessionLocal, init_db, seed_default_stakeholders
from app.models import HealthResponse
from app.routers import (
    conflicts_router,
    evaluate_router,
    frameworks_router,
    stakeholders_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_default_stakeholders(db)
    yield


app = FastAPI(
    title="MEDF API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(frameworks_router, prefix="/api")
app.include_router(stakeholders_router, prefix="/api")
app.include_router(evaluate_router, prefix="/api")
app.include_router(conflicts_router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="medf-api")
