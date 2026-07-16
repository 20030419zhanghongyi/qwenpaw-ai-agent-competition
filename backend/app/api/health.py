"""API and database health endpoint."""

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.db.health import ping_database

logger = logging.getLogger("macau_storywalk.health")
router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    env: str
    dashscope_configured: bool
    amap_configured: bool
    database_status: Literal["ok", "unavailable"]


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Check API and database health",
    description="Always returns API health and reports database availability separately.",
)
def health() -> HealthResponse:
    try:
        database_status = "ok" if ping_database() else "unavailable"
    except Exception as exc:
        logger.warning("Database health check unavailable: %s", type(exc).__name__)
        database_status = "unavailable"
    return HealthResponse(
        status="ok",
        env=settings.app_env,
        dashscope_configured=bool(settings.dashscope_api_key),
        # Either key enables an AMap capability: the JS key serves the frontend,
        # while the Web Service key is used by backend walking directions.
        amap_configured=bool(settings.amap_api_key or settings.amap_web_service_key),
        database_status=database_status,
    )
