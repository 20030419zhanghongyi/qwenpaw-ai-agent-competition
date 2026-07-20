"""Typed request and response models for Demo trips."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TripStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Trip(BaseModel):
    trip_id: str
    user_id: str
    route_id: str
    status: TripStatus
    stop_poi_ids: list[str] = Field(default_factory=list)
    checked_in_poi_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TripProgress(BaseModel):
    total_stops: int
    completed_stops: int
    completion_ratio: float = Field(ge=0.0, le=1.0)
    next_poi_id: str | None


class TripCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)
    stop_poi_ids: list[str] | None = Field(
        default=None,
        description=(
            "Optional ordered stops from the constructed / adjusted walk; "
            "overrides template nodes when provided."
        ),
    )


class CheckinRequest(BaseModel):
    poi_id: str = Field(min_length=1)


class TripResponse(Trip):
    pass


class TripProgressResponse(TripProgress):
    pass


class TripWithProgressResponse(BaseModel):
    trip: TripResponse
    progress: TripProgressResponse
