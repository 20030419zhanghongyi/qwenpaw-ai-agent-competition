"""Typed request, storage, and response models for the personal profile MVP."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.features.trips.models import TripStatus


class FavoritePoi(BaseModel):
    user_id: str
    poi_id: str
    created_at: datetime


class FavoritePoiResponse(BaseModel):
    user_id: str
    poi_id: str
    poi_name: str
    longitude: float
    latitude: float
    created_at: datetime


class TripFeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
    route_reasonable: bool | None = None
    walking_comfortable: bool | None = None

    @field_validator("comment", mode="before")
    @classmethod
    def normalize_comment(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class TripFeedback(BaseModel):
    feedback_id: str
    trip_id: str
    user_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
    route_reasonable: bool | None = None
    walking_comfortable: bool | None = None
    created_at: datetime
    updated_at: datetime


class HistoryTripResponse(BaseModel):
    trip_id: str
    route_id: str
    status: TripStatus
    created_at: datetime
    updated_at: datetime
    total_stops: int
    completed_stops: int
    completion_ratio: float = Field(ge=0.0, le=1.0)
