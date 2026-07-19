"""Import all ORM models so SQLAlchemy and Alembic can discover their tables."""

from .audit import AuditEvent
from .profile import Favorite, TripFeedback
from .poi import Poi
from .route import RouteTemplate, RouteTemplateStop
from .trip import Checkin, Postcard, Trip, TripStop
from .user import User

__all__ = [
    "Checkin",
    "AuditEvent",
    "Favorite",
    "Poi",
    "Postcard",
    "RouteTemplate",
    "RouteTemplateStop",
    "Trip",
    "TripFeedback",
    "TripStop",
    "User",
]
