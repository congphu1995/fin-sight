from fastapi import APIRouter

from app.agent.api import router as agent_router
from app.health.api import router as health_router
from app.reports.api import router as reports_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(agent_router)
api_router.include_router(reports_router)
