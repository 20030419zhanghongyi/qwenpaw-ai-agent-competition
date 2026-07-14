"""POI response models."""

from datetime import datetime

from pydantic import BaseModel, Field


class PoiResponse(BaseModel):
    poi_id: str
    poi_name: str
    alias: str | None
    address: str
    longitude: float
    latitude: float
    category: str
    source: str
    created_at: datetime
    updated_at: datetime


class NearbyPoiResponse(PoiResponse):
    distance_m: float = Field(ge=0)
