"""Story content, session lifecycle, and action orchestration."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.features.trips.service import TripService, trip_service

from .content import (
    chapter_by_id,
    load_story,
    localize_story,
    normalize_story_language,
    public_chapter,
    public_story,
    story_overview,
    story_nodes,
)
from .engine import TransitionResult, allowed_actions, apply_action
from .models import (
    StoryActionRequest,
    StoryActionResponse,
    StoryProgressResponse,
    StoryReward,
    StorySession,
    StorySessionResponse,
    StorySessionState,
    StorySessionStatus,
)
from .repository import StorySessionRepository, story_session_repository


class StorySessionNotFoundError(LookupError):
    pass


class StorySessionOwnershipError(PermissionError):
    pass


class StoryContentVersionError(RuntimeError):
    pass


class StoryService:
    def __init__(
        self,
        repository: StorySessionRepository,
        trips: TripService,
    ) -> None:
        self._repository = repository
        self._trips = trips

    @staticmethod
    def get_story(story_id: str, *, language: str = "zh-CN") -> dict[str, Any]:
        return story_overview(localize_story(load_story(story_id), language))

    def start(
        self,
        story_id: str,
        user_id: str,
        *,
        language: str = "zh-CN",
        scheduled_day: int | None = None,
        scheduled_date: date | None = None,
    ) -> StorySessionResponse:
        story = load_story(story_id)
        existing = self._repository.get_active(user_id, story_id)
        if (
            existing is not None
            and existing.state.content_version == story["version"]
        ):
            if scheduled_day is not None or scheduled_date is not None:
                existing.state.scheduled_day = scheduled_day
                existing.state.scheduled_date = scheduled_date
                existing.updated_at = datetime.now(timezone.utc)
                existing = self._repository.save(existing)
            return self._response(story, existing, language=language)

        story_stop_poi_ids = [
            str(node["poi_id"])
            for node in sorted(story_nodes(story), key=lambda item: item["order"])
            if node.get("poi_id")
        ]
        trip = self._trips.create_trip(
            user_id,
            story["route_id"],
            stop_poi_ids=story_stop_poi_ids,
        )
        now = datetime.now(timezone.utc)
        first_chapter = min(story_nodes(story), key=lambda item: item["order"])
        story_session = StorySession(
            session_id=str(uuid4()),
            user_id=user_id,
            story_id=story_id,
            trip_id=trip.trip.trip_id,
            current_chapter_id=first_chapter["id"],
            status=StorySessionStatus.ACTIVE,
            state=StorySessionState(
                content_version=story["version"],
                scheduled_day=scheduled_day,
                scheduled_date=scheduled_date,
            ),
            created_at=now,
            updated_at=now,
        )
        return self._response(
            story,
            self._repository.create(story_session),
            language=language,
        )

    def get_session(
        self, session_id: str, user_id: str, *, language: str = "zh-CN"
    ) -> StorySessionResponse:
        story_session = self._repository.get(session_id)
        if story_session is None:
            raise StorySessionNotFoundError(f"Story session not found: {session_id}")
        self._require_owner(story_session, user_id)
        story = load_story(story_session.story_id)
        self._require_current_version(story, story_session)
        return self._response(story, story_session, language=language)

    def get_active_session(
        self, story_id: str, user_id: str, *, language: str = "zh-CN"
    ) -> StorySessionResponse:
        story_session = self._repository.get_active(user_id, story_id)
        if story_session is None:
            raise StorySessionNotFoundError(
                f"Active story session not found: {story_id}"
            )
        story = load_story(story_id)
        self._require_current_version(story, story_session)
        return self._response(story, story_session, language=language)

    def act(
        self,
        session_id: str,
        user_id: str,
        request: StoryActionRequest,
        *,
        language: str = "zh-CN",
    ) -> StoryActionResponse:
        story_session = self._repository.get(session_id)
        if story_session is None:
            raise StorySessionNotFoundError(f"Story session not found: {session_id}")
        self._require_owner(story_session, user_id)
        story = load_story(story_session.story_id)
        self._require_current_version(story, story_session)
        result = apply_action(story, story_session, request)

        if result.changed and request.action.value == "arrive":
            chapter = chapter_by_id(story, request.chapter_id)
            poi_id = chapter.get("poi_id")
            if poi_id:
                self._trips.check_in(story_session.trip_id, poi_id)

        if result.changed:
            story_session = self._repository.save(story_session)
        return self._action_response(story, story_session, result, language=language)

    @staticmethod
    def _progress(
        story: dict[str, Any], story_session: StorySession
    ) -> StoryProgressResponse:
        puzzle_ids = {
            chapter["id"]
            for chapter in story_nodes(story)
            if chapter["kind"] == "puzzle"
        }
        completed = set(story_session.state.completed_chapter_ids)
        skipped = set(story_session.state.skipped_chapter_ids)
        hinted = set(story_session.state.hinted_chapter_ids)
        return StoryProgressResponse(
            total_chapters=len(story_nodes(story)),
            completed_chapters=len(completed | skipped),
            total_puzzles=len(puzzle_ids),
            solved_puzzles=len(completed & puzzle_ids),
            hinted_puzzles=len(hinted & puzzle_ids),
            skipped_puzzles=len(skipped & puzzle_ids),
        )

    @staticmethod
    def _ending(
        story: dict[str, Any], story_session: StorySession, *, language: str
    ) -> dict[str, Any] | None:
        ending_id = story_session.state.ending_id
        if ending_id is None:
            return None
        return next(
            (
                ending
                for ending in public_story(localize_story(story, language))["endings"]
                if ending["id"] == ending_id
            ),
            None,
        )

    def _response(
        self,
        story: dict[str, Any],
        story_session: StorySession,
        *,
        language: str = "zh-CN",
    ) -> StorySessionResponse:
        display_story = localize_story(story, normalize_story_language(language))
        current = None
        if story_session.status != StorySessionStatus.COMPLETED:
            current = public_chapter(
                chapter_by_id(display_story, story_session.current_chapter_id)
            )
            if current["kind"] == "ending":
                current["ending_options"] = story_overview(display_story)["endings"]
        display_state = story_session.state.model_copy(
            update={
                "rewards": self._localized_rewards(
                    display_story,
                    story_session.state.rewards,
                )
            },
            deep=True,
        )
        return StorySessionResponse(
            session_id=story_session.session_id,
            user_id=story_session.user_id,
            story_id=story_session.story_id,
            trip_id=story_session.trip_id,
            current_chapter_id=story_session.current_chapter_id,
            status=story_session.status,
            state=display_state,
            current_chapter=current,
            ending=self._ending(story, story_session, language=language),
            allowed_actions=allowed_actions(story, story_session),
            progress=self._progress(story, story_session),
            created_at=story_session.created_at,
            updated_at=story_session.updated_at,
            completed_at=story_session.completed_at,
        )

    @staticmethod
    def _require_owner(story_session: StorySession, user_id: str) -> None:
        if story_session.user_id != user_id:
            raise StorySessionOwnershipError("无权访问该故事会话")

    @staticmethod
    def _require_current_version(
        story: dict[str, Any], story_session: StorySession
    ) -> None:
        if story_session.state.content_version != story["version"]:
            raise StoryContentVersionError(
                "该会话属于旧版故事内容，请从故事封面开始 V4 新会话"
            )

    def _action_response(
        self,
        story: dict[str, Any],
        story_session: StorySession,
        result: TransitionResult,
        *,
        language: str = "zh-CN",
    ) -> StoryActionResponse:
        display_story = localize_story(story, normalize_story_language(language))
        return StoryActionResponse(
            accepted=result.accepted,
            message=result.message,
            hint=result.hint,
            new_clues=result.new_clues,
            new_rewards=self._localized_rewards(display_story, result.new_rewards),
            session=self._response(story, story_session, language=language),
        )

    @staticmethod
    def _localized_rewards(
        display_story: dict[str, Any],
        rewards: list[StoryReward],
    ) -> list[StoryReward]:
        catalog: dict[str, StoryReward] = {}

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                for key in ("reward", "reward_clue"):
                    candidate = value.get(key)
                    if isinstance(candidate, dict) and candidate.get("id"):
                        localized = StoryReward.model_validate(
                            {"kind": "stamp", **candidate}
                            if "kind" not in candidate
                            else candidate
                        )
                        catalog[localized.id] = localized
                candidates = value.get("rewards")
                if isinstance(candidates, list):
                    for candidate in candidates:
                        if isinstance(candidate, dict) and candidate.get("id"):
                            localized = StoryReward.model_validate(candidate)
                            catalog[localized.id] = localized
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(display_story)
        return [catalog.get(reward.id, reward).model_copy(deep=True) for reward in rewards]


story_service = StoryService(story_session_repository, trip_service)
