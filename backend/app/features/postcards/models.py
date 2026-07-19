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
    image_url: str
    created_at: datetime


class PostcardListResponse(BaseModel):
    postcards: list[PostcardResponse]
