"""Import all ORM models so SQLAlchemy and Alembic can discover their tables."""

from .profile import Favorite, TripFeedback
from .poi import Poi
from .route import RouteTemplate, RouteTemplateStop
from .trip import Checkin, Trip, TripStop
from .user import User

__all__ = [
    "Checkin",
    "Favorite",
    "Poi",
    "RouteTemplate",
    "RouteTemplateStop",
    "Trip",
    "TripFeedback",
    "TripStop",
    "User",
]
