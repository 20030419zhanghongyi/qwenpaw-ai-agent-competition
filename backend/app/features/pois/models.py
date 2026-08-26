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
    summary_zh_cn: str | None = None
    summary_zh_tw: str | None = None
    summary_en: str | None = None
    summary_pt: str | None = None


class NearbyPoiResponse(PoiResponse):
    distance_m: float = Field(ge=0)
