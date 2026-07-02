from fastapi import APIRouter

from app.api import health, pois, users
from app.features.routes import api as routes_api

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(routes_api.router)
api_router.include_router(pois.router)
