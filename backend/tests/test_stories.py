"""Story Package V4 workflow, privacy, version, and ownership coverage."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select

from app.db.models import Checkin, StorySession as StorySessionRecord
from app.db.models import Trip, TripStop, User
from app.db.session import SessionLocal
from app.features.stories.content import (
    load_story,
    localize_story,
    public_story,
    story_nodes,
)
from app.features.stories.engine import apply_action
from app.features.stories.models import (
    StoryAction,
    StoryActionRequest,
    StorySession,
    StorySessionState,
    StorySessionStatus,
)
from app.features.stories.service import StoryContentVersionError, StoryService
from app.main import app


STORY_ID = "lotus_city_double_map"
V4_NODE_IDS = [
    "prologue_old_book",
    "chapter_ama",
    "chapter_mandarin_house",
    "chapter_senado",
    "chapter_sam_kai",
    "chapter_lou_kau",
    "chapter_mount_fortress",
]
V4_POI_IDS = [
    "poi_0011",
    "poi_0015",
    "poi_0004",
    "poi_0136",
    "poi_0057",
    "poi_0003",
]


def _session(*, content_version: int = 4) -> StorySession:
    now = datetime.now(timezone.utc)
    return StorySession(
        session_id="story-session-test",
        user_id="story-user-test",
        story_id=STORY_ID,
        trip_id="trip-test",
        current_chapter_id="prologue_old_book",
        status=StorySessionStatus.ACTIVE,
        state=StorySessionState(content_version=content_version),
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


def _register_headers(client: TestClient, label: str) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": f"{label}-{uuid4().hex[:12]}@test.local",
            "password": "StoryPassword123!",
            "name": label,
            "language": "zh-CN",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["user_id"], {"Authorization": f"Bearer {body['token']}"}


def _complete_workflow(story: dict, story_session: StorySession) -> None:
    for node in sorted(story_nodes(story), key=lambda item: item["order"]):
        assert story_session.current_chapter_id == node["id"]
        if node.get("poi_id"):
            apply_action(story, story_session, _action(StoryAction.ARRIVE, node["id"]))
        if node["kind"] == "puzzle":
            apply_action(
                story,
                story_session,
                _action(
                    StoryAction.ANSWER,
                    node["id"],
                    answer=node["puzzle"]["solution"],
                ),
            )
        elif node["kind"] == "prologue":
            apply_action(story, story_session, _action(StoryAction.CONTINUE, node["id"]))
        else:
            apply_action(
                story,
                story_session,
                _action(
                    StoryAction.CHOOSE_ENDING,
                    node["id"],
                    choice_id="complete_today_note",
                    reflection="今天的澳门仍在变化，我把所见、年代和来源留给后来人。",
                ),
            )


def test_v4_public_package_matches_frozen_six_stop_story_and_hides_solutions():
    story = load_story(STORY_ID)
    public = public_story(story)
    nodes = story_nodes(story)

    assert story["version"] == 4
    assert story["title"] == "莲城双图：未尽之图"
    assert story["product_mode"] == "mobile_portrait_web"
    assert [node["id"] for node in nodes] == V4_NODE_IDS
    assert [node["poi_id"] for node in nodes if node.get("poi_id")] == V4_POI_IDS
    assert len(story["endings"]) == 1
    assert story["endings"][0]["id"] == "complete_today_note"
    assert all("solution" not in node.get("puzzle", {}) for node in story_nodes(public))
    assert "solution" not in str(public)
    assert "哪吒" not in str(story)
    assert "红绫" not in str(story)
    assert "消失的界线" not in str(story)


def test_v4_every_location_exposes_portrait_assets_dialogue_and_agent_context():
    story = load_story(STORY_ID)
    location_nodes = [node for node in story_nodes(story) if node.get("poi_id")]

    assert len(location_nodes) == 6
    for node in location_nodes:
        assert node["arrival_comic"]
        assert node["dialogue"]
        assert node["presentation"]["layout"].startswith("portrait_")
        assert node["presentation"]["assets"]
        assert node["agent_context"]["persona"] == "阿莲"
        assert node["agent_context"]["suggested_questions"]
        assert node["agent_context"]["do_not_reveal"]
        assert "solution" not in str(node["agent_context"])


def test_story_content_endpoint_never_exposes_puzzle_solutions():
    response = TestClient(app).get(f"/api/v1/stories/{STORY_ID}")

    assert response.status_code == 200
    assert response.json()["version"] == 4
    assert response.json()["title"] == "莲城双图：未尽之图"
    assert response.json()["presentation"]["default_orientation"] == "portrait"
    assert "solution" not in response.text


@pytest.mark.parametrize(
    ("language", "expected_title", "expected_first_stop"),
    [
        ("zh-TW", "蓮城雙圖：未竟之圖", "媽閣廟"),
        ("en", "Lotus City, Two Maps: The Map Still Unfinished", "A-Ma Temple"),
        ("pt", "Cidade de Lótus, Dois Mapas: O Mapa Inacabado", "Templo de A-Má"),
    ],
)
def test_story_locale_overlay_changes_display_text_but_preserves_puzzle_solution(
    language: str, expected_title: str, expected_first_stop: str
):
    story = load_story(STORY_ID)
    localized = localize_story(story, language)

    assert localized["title"] == expected_title
    assert story_nodes(localized)[1]["location_name"] == expected_first_stop
    assert story_nodes(localized)[1]["puzzle"]["solution"] == story_nodes(story)[1]["puzzle"]["solution"]


def test_story_content_endpoint_returns_requested_locale_without_solutions():
    response = TestClient(app).get(f"/api/v1/stories/{STORY_ID}?language=en")

    assert response.status_code == 200
    assert response.json()["title"] == "Lotus City, Two Maps: The Map Still Unfinished"
    assert "solution" not in response.text


def test_v4_unordered_answers_and_mapping_keys_are_normalized():
    story = load_story(STORY_ID)
    story_session = _session()
    apply_action(story, story_session, _action(StoryAction.CONTINUE, "prologue_old_book"))

    apply_action(story, story_session, _action(StoryAction.ARRIVE, "chapter_ama"))
    ama = apply_action(
        story,
        story_session,
        _action(
            StoryAction.ANSWER,
            "chapter_ama",
            answer=["HILL", " temple "],
        ),
    )
    assert ama.accepted is True
    assert ama.new_clues == ["note_petal_1"]

    apply_action(
        story,
        story_session,
        _action(StoryAction.ARRIVE, "chapter_mandarin_house"),
    )
    mapping_answer = {
        "water": "water_lane",
        "metal": "door_fitting",
        "earth": "courtyard",
        "fire": "skylight",
        "wood": "beam",
    }
    mandarin = apply_action(
        story,
        story_session,
        _action(
            StoryAction.ANSWER,
            "chapter_mandarin_house",
            answer=mapping_answer,
        ),
    )
    assert mandarin.accepted is True
    assert mandarin.new_rewards[0].kind == "note_petal"


def test_hint_skip_and_arrival_remain_idempotent():
    story = load_story(STORY_ID)
    story_session = _session()
    apply_action(story, story_session, _action(StoryAction.CONTINUE, "prologue_old_book"))

    arrived = apply_action(story, story_session, _action(StoryAction.ARRIVE, "chapter_ama"))
    arrived_again = apply_action(
        story, story_session, _action(StoryAction.ARRIVE, "chapter_ama")
    )
    wrong = apply_action(
        story,
        story_session,
        _action(StoryAction.ANSWER, "chapter_ama", answer=["coast", "modern_road"]),
    )
    hinted = apply_action(story, story_session, _action(StoryAction.HINT, "chapter_ama"))
    skipped = apply_action(story, story_session, _action(StoryAction.SKIP, "chapter_ama"))
    skipped_again = apply_action(
        story, story_session, _action(StoryAction.SKIP, "chapter_ama")
    )

    assert arrived.accepted is True
    assert arrived_again.changed is False
    assert wrong.accepted is False
    assert story_session.state.attempts["chapter_ama"] == 1
    assert hinted.hint
    assert skipped.new_rewards[0].kind == "note_petal"
    assert skipped.new_clues == ["note_petal_1"]
    assert skipped_again.changed is False
    assert story_session.current_chapter_id == "chapter_mandarin_house"


def test_complete_v4_workflow_awards_five_petals_and_single_ending_rewards():
    story = load_story(STORY_ID)
    story_session = _session()
    _complete_workflow(story, story_session)

    reward_ids = [reward.id for reward in story_session.state.rewards]
    note_petal_ids = [
        reward.id
        for reward in story_session.state.rewards
        if reward.kind == "note_petal"
    ]
    assert story_session.status == StorySessionStatus.COMPLETED
    assert story_session.state.ending_id == "complete_today_note"
    assert story_session.state.ending_reflection == (
        "今天的澳门仍在变化，我把所见、年代和来源留给后来人。"
    )
    assert note_petal_ids == [f"note_petal_{index}" for index in range(1, 6)]
    assert reward_ids[-2:] == ["complete_city_flower", "today_note"]
    assert len(story_session.state.completed_chapter_ids) == 7


def test_old_content_session_is_rejected_instead_of_using_v4_nodes():
    story = load_story(STORY_ID)
    story_session = _session(content_version=3)

    with pytest.raises(StoryContentVersionError):
        StoryService._require_current_version(story, story_session)


def test_story_api_requires_owner_and_runs_complete_v4_workflow():
    client = TestClient(app)
    story = load_story(STORY_ID)
    owner_id, owner_headers = _register_headers(client, "story-owner")
    other_id, other_headers = _register_headers(client, "story-other")
    session_id = ""
    trip_id = ""
    try:
        missing_auth = client.post(f"/api/v1/stories/{STORY_ID}/sessions")
        assert missing_auth.status_code == 401

        started = client.post(
            f"/api/v1/stories/{STORY_ID}/sessions", headers=owner_headers
        )
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]
        trip_id = started.json()["trip_id"]
        assert started.json()["state"]["content_version"] == 4

        resumed = client.post(
            f"/api/v1/stories/{STORY_ID}/sessions", headers=owner_headers
        )
        assert resumed.status_code == 201
        assert resumed.json()["session_id"] == session_id
        assert (
            client.get(
                f"/api/v1/story-sessions/{session_id}", headers=other_headers
            ).status_code
            == 403
        )

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
            elif node["kind"] == "prologue":
                payload = {"action": "continue", "chapter_id": node["id"]}
            else:
                payload = {
                    "action": "choose_ending",
                    "chapter_id": node["id"],
                    "choice_id": "complete_today_note",
                    "reflection": "今日补记：记录今天，也注明今天。",
                }
            progressed = client.post(
                f"/api/v1/story-sessions/{session_id}/actions",
                headers=owner_headers,
                json=payload,
            )
            assert progressed.status_code == 200, progressed.text
            assert progressed.json()["accepted"] is True

        restored = client.get(
            f"/api/v1/story-sessions/{session_id}", headers=owner_headers
        )
        assert restored.status_code == 200
        assert restored.json()["status"] == "completed"
        assert restored.json()["state"]["ending_id"] == "complete_today_note"
        assert restored.json()["progress"] == {
            "total_chapters": 7,
            "completed_chapters": 7,
            "total_puzzles": 5,
            "solved_puzzles": 5,
            "hinted_puzzles": 0,
            "skipped_puzzles": 0,
        }
        trip_progress = client.get(f"/api/v1/trips/{trip_id}/progress")
        assert trip_progress.status_code == 200
        assert trip_progress.json()["completed_stops"] == 6
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
                for user_id in (owner_id, other_id):
                    remaining_trips = database.scalar(
                        select(Trip.id).where(Trip.user_id == user_id).limit(1)
                    )
                    if remaining_trips is None:
                        database.execute(delete(User).where(User.id == user_id))
                database.commit()
