"""Public request and response contracts for personalized postcards."""

from datetime import datetime

from pydantic import BaseModel, Field


class PostcardResponse(BaseModel):
    postcard_id: str
    trip_id: str
    poi_id: str
    poi_name: str
    stop_order: int = Field(ge=0)
    caption: str
    caption_source: str
    source_type: str
    ai_generated: bool
    language: str
    review_decision: str
    photo_scrubbed: bool
    has_user_photo: bool = True
    # New records: user | ai_edit | ai. Legacy records may report library | placeholder.
    scene_source: str = "user"
    photo_style: str | None = None
    image_url: str
    created_at: datetime
    # Design stamps: time / public POI geo / route task (not photo EXIF).
    visited_at: datetime | None = None
    timestamp_label: str = ""
    geo_label: str = ""
    latitude: float | None = None
    longitude: float | None = None
    district: str | None = None
    route_id: str | None = None
    route_name: str | None = None
    task_label: str = ""


class PostcardListResponse(BaseModel):
    postcards: list[PostcardResponse]


class PostcardPrewarmResponse(BaseModel):
    status: str = "queued"
    trip_id: str
    poi_id: str
