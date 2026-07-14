from fastapi import APIRouter

from app.agents import api as agents_api
from app.api import health
from app.features.guide import api as guide_api
from app.features.intent import api as intent_api
from app.features.pois import api as pois_api
from app.features.profile import api as profile_api
from app.features.review import api as review_api
from app.features.routes import api as routes_api
from app.features.trips import api as trips_api
from app.features.users import api as users_api
from app.orchestrator import api as orchestrator_api

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users_api.router)
api_router.include_router(routes_api.router)
api_router.include_router(trips_api.router)
api_router.include_router(trips_api.user_router)
api_router.include_router(profile_api.user_router)
api_router.include_router(profile_api.trip_router)
api_router.include_router(intent_api.router)
api_router.include_router(review_api.router)
api_router.include_router(guide_api.router)
api_router.include_router(pois_api.router)
api_router.include_router(agents_api.router)
api_router.include_router(orchestrator_api.router)
