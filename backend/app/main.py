"""QwenPaw FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(level=settings.log_level.upper())


class RootResponse(BaseModel):
    name: str
    docs: str
    health: str


OPENAPI_TAGS = [
    {"name": "health", "description": "API and PostgreSQL availability."},
    {"name": "pois", "description": "Canonical POI and PostGIS nearby queries."},
    {"name": "routes", "description": "Persisted route templates and matching."},
    {"name": "trips", "description": "Trip lifecycle, check-ins, and progress."},
    {"name": "profile", "description": "Trip history, favorites, and feedback."},
    {"name": "users", "description": "Demo user preference endpoints."},
]

app = FastAPI(
    title="QwenPaw Macau AI Travel Assistant API",
    description=(
        "Stable backend data API for the QwenPaw Agent and mini-program teams. "
        "Core POI, route, trip, check-in, favorite, and feedback data is persisted "
        "in PostgreSQL/PostGIS."
    ),
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
    contact={"name": "QwenPaw backend team"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", response_model=RootResponse, summary="API entry point")
def root() -> RootResponse:
    return RootResponse(
        name="QwenPaw Macau AI Travel Assistant API",
        docs="/docs",
        health="/api/v1/health",
    )
