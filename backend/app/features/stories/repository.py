"""PostgreSQL persistence for story-route sessions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import StorySession as StorySessionRecord
from app.db.session import SessionLocal

from .models import StorySession, StorySessionState, StorySessionStatus


class StorySessionRepository:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _to_domain(record: StorySessionRecord) -> StorySession:
        return StorySession(
            session_id=record.id,
            user_id=record.user_id,
            story_id=record.story_id,
            trip_id=record.trip_id,
            current_chapter_id=record.current_chapter_id,
            status=StorySessionStatus(record.status),
            state=StorySessionState.model_validate(record.state),
            created_at=record.created_at,
            updated_at=record.updated_at,
            completed_at=record.completed_at,
        )

    def get(self, session_id: str) -> StorySession | None:
        with self._session_factory() as session:
            record = session.get(StorySessionRecord, session_id)
            return self._to_domain(record) if record is not None else None

    def get_active(self, user_id: str, story_id: str) -> StorySession | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(StorySessionRecord)
                .where(
                    StorySessionRecord.user_id == user_id,
                    StorySessionRecord.story_id == story_id,
                    StorySessionRecord.status == StorySessionStatus.ACTIVE.value,
                )
                .order_by(StorySessionRecord.created_at.desc())
                .limit(1)
            )
            return self._to_domain(record) if record is not None else None

    def create(self, story_session: StorySession) -> StorySession:
        record = StorySessionRecord(
            id=story_session.session_id,
            user_id=story_session.user_id,
            story_id=story_session.story_id,
            trip_id=story_session.trip_id,
            current_chapter_id=story_session.current_chapter_id,
            status=story_session.status.value,
            state=story_session.state.model_dump(mode="json"),
            created_at=story_session.created_at,
            updated_at=story_session.updated_at,
            completed_at=story_session.completed_at,
        )
        with self._session_factory() as session:
            session.add(record)
            session.commit()
            return self._to_domain(record)

    def save(self, story_session: StorySession) -> StorySession:
        with self._session_factory() as session:
            record = session.get(StorySessionRecord, story_session.session_id)
            if record is None:
                raise LookupError(f"Story session not found: {story_session.session_id}")
            record.current_chapter_id = story_session.current_chapter_id
            record.status = story_session.status.value
            record.state = story_session.state.model_dump(mode="json")
            record.updated_at = datetime.now(timezone.utc)
            record.completed_at = story_session.completed_at
            session.commit()
            return self._to_domain(record)


story_session_repository = StorySessionRepository()
