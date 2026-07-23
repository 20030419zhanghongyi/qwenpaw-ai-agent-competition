"""API and domain models for story-route sessions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StorySessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class StoryAction(str, Enum):
    ARRIVE = "arrive"
    COLLECT = "collect"
    ANSWER = "answer"
    HINT = "hint"
    SKIP = "skip"
    CONTINUE = "continue"
    CHOOSE_ENDING = "choose_ending"


class StorySessionState(BaseModel):
    arrived_chapter_ids: list[str] = Field(default_factory=list)
    completed_chapter_ids: list[str] = Field(default_factory=list)
    hinted_chapter_ids: list[str] = Field(default_factory=list)
    skipped_chapter_ids: list[str] = Field(default_factory=list)
    clues: list[str] = Field(default_factory=list)
    collectibles: list[str] = Field(default_factory=list)
    unlocked_bonus_ids: list[str] = Field(default_factory=list)
    choices: dict[str, str] = Field(default_factory=dict)
    attempts: dict[str, int] = Field(default_factory=dict)
    hint_counts: dict[str, int] = Field(default_factory=dict)
    ending_id: str | None = None


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


class StoryStartRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)


class StoryActionRequest(BaseModel):
    action: StoryAction
    chapter_id: str = Field(min_length=1, max_length=128)
    answer: Any | None = None
    choice_id: str | None = Field(default=None, max_length=128)
    collectible_id: str | None = Field(default=None, max_length=128)


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
    session: StorySessionResponse
