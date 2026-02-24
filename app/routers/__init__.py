from app.routers.conflicts import router as conflicts_router
from app.routers.evaluate import router as evaluate_router
from app.routers.frameworks import router as frameworks_router
from app.routers.stakeholders import router as stakeholders_router

__all__ = [
    "conflicts_router",
    "evaluate_router",
    "frameworks_router",
    "stakeholders_router",
]
