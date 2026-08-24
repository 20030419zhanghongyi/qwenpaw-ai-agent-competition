"""API contracts for personal travel memoirs."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MemoirStyle = Literal["diary", "magazine", "social", "documentary"]


class MemoirCreateRequest(BaseModel):
    style: MemoirStyle = "diary"
    language: str = Field(default="zh-CN", max_length=16)


class MemoirChapter(BaseModel):
    poi_id: str
    poi_name: str
    stop_order: int = Field(ge=0)
    body: str = Field(default="", max_length=3000)
    personal_note: str = Field(default="", max_length=3000)
    included: bool = True
    postcard_id: str | None = None
    postcard_caption: str | None = None
    postcard_image_url: str | None = None


class MemoirPhotoResponse(BaseModel):
    photo_id: str
    poi_id: str | None
    filename: str
    content_type: str
    has_people: bool
    image_url: str
    created_at: datetime


class MemoirUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    style: MemoirStyle | None = None
    introduction: str | None = Field(default=None, max_length=5000)
    closing: str | None = Field(default=None, max_length=5000)
    status: Literal["draft", "completed"] | None = None
    cover_photo_id: str | None = None
    chapters: list[MemoirChapter] | None = None


class MemoirResponse(BaseModel):
    memoir_id: str
    trip_id: str
    user_id: str
    route_id: str
    trip_status: str
    travel_date: datetime | None
    title: str
    style: MemoirStyle
    language: str
    introduction: str
    closing: str
    status: str
    chapters: list[MemoirChapter]
    photos: list[MemoirPhotoResponse]
    cover_photo_id: str | None
    active_share_token: str | None = None
    created_at: datetime
    updated_at: datetime


class MemoirSummary(BaseModel):
    trip_id: str
    memoir_id: str | None = None
    status: str | None = None


class SharePrivacy(BaseModel):
    hide_people_photos: bool = True
    hide_date: bool = False
    hide_exact_route: bool = False
    hide_personal_notes: bool = False


class ShareResponse(BaseModel):
    token: str
    share_url: str
    privacy: SharePrivacy


class SharedMemoirResponse(BaseModel):
    title: str
    style: MemoirStyle
    language: str
    introduction: str
    closing: str
    route_id: str | None
    travel_date: datetime | None
    chapters: list[MemoirChapter]
    photos: list[MemoirPhotoResponse]
    cover_photo_id: str | None
