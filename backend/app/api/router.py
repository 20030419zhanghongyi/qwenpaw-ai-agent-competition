from fastapi import APIRouter

from app.agents import api as agents_api
from app.api import health, pois, users
from app.features.routes import api as routes_api

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(routes_api.router)
api_router.include_router(pois.router)
api_router.include_router(agents_api.router)
