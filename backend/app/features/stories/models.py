"""API and domain models for story-route sessions."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StorySessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class StoryAction(str, Enum):
    ARRIVE = "arrive"
    ANSWER = "answer"
    HINT = "hint"
    SKIP = "skip"
    CONTINUE = "continue"
    CHOOSE_ENDING = "choose_ending"


class StoryReward(BaseModel):
    """A durable story reward. ``clues`` remains for legacy clients."""

    id: str
    kind: str
    name: str | None = None
    text: str | None = None


class StorySessionState(BaseModel):
    content_version: int = Field(default=1, ge=1)
    scheduled_day: int | None = Field(default=None, ge=1, le=5)
    scheduled_date: date | None = None
    arrived_chapter_ids: list[str] = Field(default_factory=list)
    completed_chapter_ids: list[str] = Field(default_factory=list)
    hinted_chapter_ids: list[str] = Field(default_factory=list)
    skipped_chapter_ids: list[str] = Field(default_factory=list)
    clues: list[str] = Field(default_factory=list)
    rewards: list[StoryReward] = Field(default_factory=list)
    choices: dict[str, str] = Field(default_factory=dict)
    attempts: dict[str, int] = Field(default_factory=dict)
    hint_counts: dict[str, int] = Field(default_factory=dict)
    ending_id: str | None = None
    ending_reflection: str | None = None


class StorySession(BaseModel):
    session_id: str
    user_id: str
    story_id: str
    trip_id: str
    current_chapter_id: str
    status: StorySessionStatus
    state: StorySessionState
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class StoryActionRequest(BaseModel):
    action: StoryAction
    chapter_id: str = Field(min_length=1, max_length=128)
    answer: Any | None = None
    choice_id: str | None = Field(default=None, max_length=128)
    reflection: str | None = Field(default=None, max_length=2000)


class StoryProgressResponse(BaseModel):
    total_chapters: int
    completed_chapters: int
    total_puzzles: int
    solved_puzzles: int
    hinted_puzzles: int
    skipped_puzzles: int


class StorySessionResponse(BaseModel):
    session_id: str
    user_id: str
    story_id: str
    trip_id: str
    current_chapter_id: str
    status: StorySessionStatus
    state: StorySessionState
    current_chapter: dict[str, Any] | None
    ending: dict[str, Any] | None
    allowed_actions: list[StoryAction]
    progress: StoryProgressResponse
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class StoryActionResponse(BaseModel):
    accepted: bool
    message: str
    hint: str | None = None
    new_clues: list[str] = Field(default_factory=list)
    new_rewards: list[StoryReward] = Field(default_factory=list)
    session: StorySessionResponse


class FutureLetterResponse(BaseModel):
    status: str = "ready"
    story_session_id: str
    postcard_id: str
    image_url: str
    scene_source: str = "ai"
    generated_at: datetime
    reflection_truncated: bool = False
