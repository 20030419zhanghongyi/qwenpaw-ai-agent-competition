"""Story Package v3, deterministic workflow, and ownership coverage."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db.models import Checkin, StorySession as StorySessionRecord
from app.db.models import Trip, TripStop, User
from app.db.session import SessionLocal
from app.features.stories.content import load_story, public_story, story_nodes
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
        current_chapter_id="prologue_time_map",
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
    reflection: str | None = None,
) -> StoryActionRequest:
    return StoryActionRequest(
        action=action,
        chapter_id=chapter_id,
        answer=answer,
        choice_id=choice_id,
        reflection=reflection,
    )


def _headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _complete_workflow(story: dict, story_session: StorySession) -> None:
    for node in sorted(story_nodes(story), key=lambda item: item["order"]):
        assert story_session.current_chapter_id == node["id"]
        if node.get("poi_id"):
            apply_action(story, story_session, _action(StoryAction.ARRIVE, node["id"]))
        if node["kind"] == "puzzle":
            apply_action(
                story,
                story_session,
                _action(StoryAction.ANSWER, node["id"], answer=node["puzzle"]["solution"]),
            )
        elif node["kind"] in {"prologue", "narrative", "transition"}:
            apply_action(story, story_session, _action(StoryAction.CONTINUE, node["id"]))
        else:
            apply_action(
                story,
                story_session,
                _action(
                    StoryAction.CHOOSE_ENDING,
                    node["id"],
                    choice_id="leave_blank",
                    reflection="让地图保留可以被未来继续追问的空白。",
                ),
            )


def test_v3_public_package_uses_nodes_and_hides_solutions():
    story = load_story(STORY_ID)
    public = public_story(story)

    assert story["version"] == 3
    assert "chapters" not in story
    assert [node["id"] for node in story_nodes(story)] == [
        "prologue_time_map",
        "chapter_ama",
        "chapter_lilau",
        "chapter_penha",
        "chapter_sam_kai",
        "chapter_lou_kau",
        "chapter_mandarin_house",
        "transition_isolated_island",
        "chapter_st_paul_walls",
        "chapter_mount_fortress",
    ]
    assert story_nodes(story)[8]["secondary_poi_ids"] == ["poi_0133"]
    assert story_nodes(story)[9]["poi_status"] == "missing_canonical_poi"
    assert all("solution" not in node.get("puzzle", {}) for node in story_nodes(public))
    card_kinds = {
        card["kind"] for node in story_nodes(story) for card in node.get("knowledge_cards", [])
    }
    assert {
        "historical_fact",
        "folklore",
        "contextual_reconstruction",
        "fictional_story",
        "dynamic_operational_info",
    } <= card_kinds


def test_story_content_endpoint_never_exposes_puzzle_solutions():
    response = TestClient(app).get(f"/api/v1/stories/{STORY_ID}")

    assert response.status_code == 200
    assert "solution" not in response.text
    assert response.json()["version"] == 3
    assert "nodes" in response.json()


def test_hint_skip_and_arrival_are_idempotent_in_v3_workflow():
    story = load_story(STORY_ID)
    story_session = _session()
    apply_action(story, story_session, _action(StoryAction.CONTINUE, "prologue_time_map"))

    arrived = apply_action(story, story_session, _action(StoryAction.ARRIVE, "chapter_ama"))
    arrived_again = apply_action(story, story_session, _action(StoryAction.ARRIVE, "chapter_ama"))
    wrong = apply_action(
        story, story_session, _action(StoryAction.ANSWER, "chapter_ama", answer="fort")
    )
    hinted = apply_action(story, story_session, _action(StoryAction.HINT, "chapter_ama"))
    skipped = apply_action(story, story_session, _action(StoryAction.SKIP, "chapter_ama"))
    skipped_again = apply_action(story, story_session, _action(StoryAction.SKIP, "chapter_ama"))

    assert arrived.accepted is True
    assert arrived_again.changed is False
    assert wrong.accepted is False
    assert story_session.state.attempts["chapter_ama"] == 1
    assert hinted.hint
    assert skipped.new_rewards[0].kind == "stamp"
    assert skipped.new_clues == ["stamp_tide"]
    assert skipped_again.changed is False
    assert story_session.current_chapter_id == "chapter_lilau"


def test_complete_v3_workflow_awards_capability_handles_transition_and_reflection():
    story = load_story(STORY_ID)
    story_session = _session()
    _complete_workflow(story, story_session)

    reward_kinds = {reward.kind for reward in story_session.state.rewards}
    assert story_session.status == StorySessionStatus.COMPLETED
    assert story_session.state.ending_id == "leave_blank"
    assert story_session.state.ending_reflection == "让地图保留可以被未来继续追问的空白。"
    assert "transition_isolated_island" in story_session.state.completed_chapter_ids
    assert {"stamp", "capability", "coordinate"} <= reward_kinds
    assert next(
        reward for reward in story_session.state.rewards if reward.id == "capability_overlay_rule"
    ).kind == "capability"


def test_story_api_requires_owner_and_runs_v3_workflow():
    client = TestClient(app)
    story = load_story(STORY_ID)
    owner_id = f"story-owner-{uuid4().hex[:12]}"
    other_id = f"story-other-{uuid4().hex[:12]}"
    owner_headers = _headers(owner_id)
    other_headers = _headers(other_id)
    session_id = ""
    trip_id = ""
    try:
        missing_auth = client.post(f"/api/v1/stories/{STORY_ID}/sessions")
        assert missing_auth.status_code == 401

        started = client.post(f"/api/v1/stories/{STORY_ID}/sessions", headers=owner_headers)
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]
        trip_id = started.json()["trip_id"]
        resumed = client.post(f"/api/v1/stories/{STORY_ID}/sessions", headers=owner_headers)
        assert resumed.status_code == 201
        assert resumed.json()["session_id"] == session_id
        assert client.get(f"/api/v1/story-sessions/{session_id}", headers=other_headers).status_code == 403
        assert client.post(
            f"/api/v1/story-sessions/{session_id}/actions",
            headers=other_headers,
            json={"action": "continue", "chapter_id": "prologue_time_map"},
        ).status_code == 403

        for node in sorted(story_nodes(story), key=lambda item: item["order"]):
            if node.get("poi_id"):
                arrived = client.post(
                    f"/api/v1/story-sessions/{session_id}/actions",
                    headers=owner_headers,
                    json={"action": "arrive", "chapter_id": node["id"]},
                )
                assert arrived.status_code == 200, arrived.text
            if node["kind"] == "puzzle":
                payload = {
                    "action": "answer",
                    "chapter_id": node["id"],
                    "answer": node["puzzle"]["solution"],
                }
            elif node["kind"] in {"prologue", "narrative", "transition"}:
                payload = {"action": "continue", "chapter_id": node["id"]}
            else:
                payload = {
                    "action": "choose_ending",
                    "chapter_id": node["id"],
                    "choice_id": "open_archive",
                    "reflection": "公开来源，也公开边界。",
                }
            progressed = client.post(
                f"/api/v1/story-sessions/{session_id}/actions",
                headers=owner_headers,
                json=payload,
            )
            assert progressed.status_code == 200, progressed.text
            assert progressed.json()["accepted"] is True

        restored = client.get(f"/api/v1/story-sessions/{session_id}", headers=owner_headers)
        assert restored.status_code == 200
        assert restored.json()["status"] == "completed"
        assert restored.json()["state"]["ending_reflection"] == "公开来源，也公开边界。"
        assert restored.json()["progress"] == {
            "total_chapters": 10,
            "completed_chapters": 10,
            "total_puzzles": 6,
            "solved_puzzles": 6,
            "hinted_puzzles": 0,
            "skipped_puzzles": 0,
        }
        trip_progress = client.get(f"/api/v1/trips/{trip_id}/progress")
        assert trip_progress.status_code == 200
        assert trip_progress.json()["completed_stops"] == 7
        assert trip_progress.json()["completion_ratio"] == 1.0
    finally:
        if trip_id:
            with SessionLocal() as database:
                database.execute(delete(StorySessionRecord).where(StorySessionRecord.id == session_id))
                database.execute(delete(Checkin).where(Checkin.trip_id == trip_id))
                database.execute(delete(TripStop).where(TripStop.trip_id == trip_id))
                database.execute(delete(Trip).where(Trip.id == trip_id))
                for user_id in (owner_id, other_id):
                    remaining_trips = database.scalar(
                        select(Trip.id).where(Trip.user_id == user_id).limit(1)
                    )
                    if remaining_trips is None:
                        database.execute(delete(User).where(User.id == user_id))
                database.commit()
