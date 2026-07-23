"""Story content and deterministic transition coverage."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.models import Checkin, StorySession as StorySessionRecord
from app.db.models import Trip, TripStop, User
from app.db.session import SessionLocal
from app.features.stories.content import load_story, public_story
from app.features.stories.engine import apply_action
from app.features.stories.models import (
    StoryAction,
    StoryActionRequest,
    StorySession,
    StorySessionState,
    StorySessionStatus,
)
from app.main import app


STORY_ID = "lotus_city_double_map"


def _session() -> StorySession:
    now = datetime.now(timezone.utc)
    return StorySession(
        session_id="story-session-test",
        user_id="story-user-test",
        story_id=STORY_ID,
        trip_id="trip-test",
        current_chapter_id="chapter_ama",
        status=StorySessionStatus.ACTIVE,
        state=StorySessionState(),
        created_at=now,
        updated_at=now,
    )


def _action(
    action: StoryAction,
    chapter_id: str,
    *,
    answer=None,
    choice_id: str | None = None,
) -> StoryActionRequest:
    return StoryActionRequest(
        action=action,
        chapter_id=chapter_id,
        answer=answer,
        choice_id=choice_id,
    )


def test_public_story_contains_seven_chapters_without_solutions():
    story = load_story(STORY_ID)
    public = public_story(story)

    assert len(public["chapters"]) == 7
    assert sum(chapter["kind"] == "puzzle" for chapter in public["chapters"]) == 5
    assert len(public["endings"]) == 3
    assert all(
        "solution" not in chapter.get("puzzle", {}) for chapter in public["chapters"]
    )
    assert all("condition" not in ending for ending in public["endings"])


def test_story_content_endpoint_never_exposes_puzzle_solutions():
    response = TestClient(app).get(f"/api/v1/stories/{STORY_ID}")

    assert response.status_code == 200
    assert "solution" not in response.text
    assert response.json()["title"] == "莲城双图：消失的界线"


def test_wrong_answer_hint_and_skip_keep_story_playable():
    story = load_story(STORY_ID)
    story_session = _session()

    arrived = apply_action(
        story,
        story_session,
        _action(StoryAction.ARRIVE, "chapter_ama"),
    )
    arrived_again = apply_action(
        story,
        story_session,
        _action(StoryAction.ARRIVE, "chapter_ama"),
    )
    wrong = apply_action(
        story,
        story_session,
        _action(StoryAction.ANSWER, "chapter_ama", answer="fort"),
    )
    hinted = apply_action(
        story,
        story_session,
        _action(StoryAction.HINT, "chapter_ama"),
    )
    skipped = apply_action(
        story,
        story_session,
        _action(StoryAction.SKIP, "chapter_ama"),
    )

    assert arrived.accepted is True
    assert arrived_again.changed is False
    assert wrong.accepted is False
    assert story_session.state.attempts["chapter_ama"] == 1
    assert hinted.hint
    assert skipped.new_clues == ["clue_tide"]
    assert story_session.state.skipped_chapter_ids == ["chapter_ama"]
    assert story_session.current_chapter_id == "chapter_mandarin_house"


def test_all_story_chapters_can_reach_an_ending_with_one_skipped_puzzle():
    story = load_story(STORY_ID)
    story_session = _session()
    chapters = sorted(story["chapters"], key=lambda item: item["order"])

    for chapter in chapters:
        assert story_session.current_chapter_id == chapter["id"]
        apply_action(
            story,
            story_session,
            _action(StoryAction.ARRIVE, chapter["id"]),
        )
        if chapter["kind"] == "puzzle":
            if chapter["id"] == "chapter_sam_kai":
                action = _action(StoryAction.SKIP, chapter["id"])
            else:
                action = _action(
                    StoryAction.ANSWER,
                    chapter["id"],
                    answer=chapter["puzzle"]["solution"],
                )
            apply_action(story, story_session, action)
        elif chapter["kind"] == "narrative":
            apply_action(
                story,
                story_session,
                _action(StoryAction.CONTINUE, chapter["id"]),
            )
        else:
            apply_action(
                story,
                story_session,
                _action(
                    StoryAction.CHOOSE_ENDING,
                    chapter["id"],
                    choice_id="open_archive",
                ),
            )

    assert story_session.status == StorySessionStatus.COMPLETED
    assert story_session.state.ending_id == "open_archive"
    assert story_session.state.skipped_chapter_ids == ["chapter_sam_kai"]
    assert story_session.state.clues == [
        "clue_tide",
        "clue_gate",
        "clue_words",
        "clue_market",
        "clue_people",
    ]


def test_story_api_runs_full_trip_and_restores_the_same_active_session():
    client = TestClient(app)
    story = load_story(STORY_ID)
    user_id = f"story-api-{uuid4().hex[:12]}"
    session_id = ""
    trip_id = ""
    try:
        started = client.post(
            f"/api/v1/stories/{STORY_ID}/sessions",
            json={"user_id": user_id},
        )
        assert started.status_code == 201
        session_id = started.json()["session_id"]
        trip_id = started.json()["trip_id"]

        resumed = client.post(
            f"/api/v1/stories/{STORY_ID}/sessions",
            json={"user_id": user_id},
        )
        assert resumed.status_code == 201
        assert resumed.json()["session_id"] == session_id

        for chapter in sorted(story["chapters"], key=lambda item: item["order"]):
            arrived = client.post(
                f"/api/v1/story-sessions/{session_id}/actions",
                json={"action": "arrive", "chapter_id": chapter["id"]},
            )
            assert arrived.status_code == 200
            if chapter["kind"] == "puzzle":
                if chapter["id"] == "chapter_sam_kai":
                    payload = {"action": "skip", "chapter_id": chapter["id"]}
                else:
                    payload = {
                        "action": "answer",
                        "chapter_id": chapter["id"],
                        "answer": chapter["puzzle"]["solution"],
                    }
            elif chapter["kind"] == "narrative":
                payload = {"action": "continue", "chapter_id": chapter["id"]}
            else:
                payload = {
                    "action": "choose_ending",
                    "chapter_id": chapter["id"],
                    "choice_id": "open_archive",
                }
            progressed = client.post(
                f"/api/v1/story-sessions/{session_id}/actions",
                json=payload,
            )
            assert progressed.status_code == 200
            assert progressed.json()["accepted"] is True

        restored = client.get(f"/api/v1/story-sessions/{session_id}")
        assert restored.status_code == 200
        assert restored.json()["status"] == "completed"
        assert restored.json()["ending"]["id"] == "open_archive"
        assert restored.json()["progress"] == {
            "total_chapters": 7,
            "completed_chapters": 7,
            "total_puzzles": 5,
            "solved_puzzles": 4,
            "hinted_puzzles": 0,
            "skipped_puzzles": 1,
        }

        trip_progress = client.get(f"/api/v1/trips/{trip_id}/progress")
        assert trip_progress.status_code == 200
        assert trip_progress.json()["completed_stops"] == 7
        assert trip_progress.json()["completion_ratio"] == 1.0
    finally:
        if trip_id:
            with SessionLocal() as database:
                database.execute(
                    delete(StorySessionRecord).where(
                        StorySessionRecord.id == session_id
                    )
                )
                database.execute(delete(Checkin).where(Checkin.trip_id == trip_id))
                database.execute(delete(TripStop).where(TripStop.trip_id == trip_id))
                database.execute(delete(Trip).where(Trip.id == trip_id))
                remaining_trips = database.scalar(
                    select(Trip.id).where(Trip.user_id == user_id).limit(1)
                )
                if remaining_trips is None:
                    database.execute(delete(User).where(User.id == user_id))
                database.commit()
