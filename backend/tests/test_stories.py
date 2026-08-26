"""Story Package V4 workflow, privacy, version, and ownership coverage."""

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from sqlalchemy import delete, select

from app.db.models import Checkin, Postcard, StorySession as StorySessionRecord
from app.db.models import Trip, TripStop, User
from app.db.session import SessionLocal
from app.features.pois.repository import PoiRepository
from app.features.postcards.scene_image import SceneGenerationError
from app.features.routes.repository import get_template
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
    StoryReward,
    StorySession,
    StorySessionState,
    StorySessionStatus,
)
from app.features.stories.service import StoryContentVersionError, StoryService
from app.main import app


STORY_ID = "lotus_city_double_map"
COLOANE_STORY_ID = "coloane_after_tide"
TAIPA_STORY_ID = "taipa_letters"
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


def _session(
    *,
    story_id: str = STORY_ID,
    current_chapter_id: str = "prologue_old_book",
    content_version: int = 4,
) -> StorySession:
    now = datetime.now(timezone.utc)
    return StorySession(
        session_id="story-session-test",
        user_id="story-user-test",
        story_id=story_id,
        trip_id="trip-test",
        current_chapter_id=current_chapter_id,
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


def _complete_workflow(
    story: dict,
    story_session: StorySession,
    *,
    ending_choice_id: str | None = None,
) -> None:
    selected_ending_id = ending_choice_id or story["endings"][0]["id"]
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
                    choice_id=selected_ending_id,
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


@pytest.mark.parametrize(
    ("story_id", "expected_route_id", "expected_title"),
    [
        ("taipa_letters", "taipa_hotspot_halfday", "海风寄来的信"),
        ("coloane_after_tide", "coloane_leisure_halfday", "潮退之后"),
    ],
)
def test_additional_story_packages_are_public_safe_and_complete(
    story_id: str,
    expected_route_id: str,
    expected_title: str,
):
    story = load_story(story_id)
    public = public_story(story)
    nodes = sorted(story_nodes(story), key=lambda item: item["order"])

    assert story["version"] == 4
    assert story["route_id"] == expected_route_id
    assert story["title"] == expected_title
    assert len(nodes) == 7
    assert [node["order"] for node in nodes] == list(range(7))
    assert all("solution" not in node.get("puzzle", {}) for node in story_nodes(public))
    assert "solution" not in str(public)

    response = TestClient(app).get(f"/api/v1/stories/{story_id}")
    assert response.status_code == 200
    assert response.json()["title"] == expected_title
    assert response.json()["nodes"][1]["location_name"]

    assert get_template(expected_route_id) is not None
    story_poi_ids = [node["poi_id"] for node in nodes if node.get("poi_id")]
    with SessionLocal() as database:
        assert set(PoiRepository(database).get_by_ids(story_poi_ids)) == set(
            story_poi_ids
        )

    now = datetime.now(timezone.utc)
    story_session = StorySession(
        session_id=f"{story_id}-session-test",
        user_id="story-user-test",
        story_id=story_id,
        trip_id="trip-test",
        current_chapter_id=nodes[0]["id"],
        status=StorySessionStatus.ACTIVE,
        state=StorySessionState(content_version=story["version"]),
        created_at=now,
        updated_at=now,
    )
    _complete_workflow(story, story_session)

    assert story_session.status == StorySessionStatus.COMPLETED
    assert story_session.state.ending_id == story["endings"][0]["id"]
    assert len(story_session.state.completed_chapter_ids) == 7


def test_taipa_package_preserves_planned_content_layers_and_fallbacks():
    story = load_story("taipa_letters")
    nodes = story_nodes(story)

    assert [node["location_name"] for node in nodes if node.get("poi_id")] == [
        "北帝庙",
        "嘉模圣母堂",
        "龙环葡韵",
        "益隆炮竹厂旧址",
        "官也街与氹仔旧城",
        "氹仔旧城公共空间",
    ]
    for node in nodes:
        assert node["time_layer"]
        assert node["letter_fragment"]
        assert node["historical_claims"]
        assert node["interaction"]
        assert node["fallback"]["text"]
        assert node["presentation"]["assets"]
        assert node["agent_context"]["fiction_boundaries"]


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


@pytest.mark.parametrize(
    ("story_id", "node_id", "language", "expected_title", "expected_caption"),
    [
        (
            "taipa_letters",
            "prologue_taipa_letter_box",
            "en",
            "Prologue: Letters with No Recipient",
            "The lid creaks open. Five unaddressed letters lie quietly together",
        ),
        (
            "taipa_letters",
            "prologue_taipa_letter_box",
            "pt",
            "Prólogo: A carta sem destinatário",
            "A tampa abre-se com um rangido. Cinco cartas sem endereço aguardam",
        ),
        (
            "coloane_after_tide",
            "prologue_tide_workbook",
            "en",
            "Prologue: The Last Page Is Blank",
            "This is not a treasure map, but a workbook waiting to be filled",
        ),
        (
            "coloane_after_tide",
            "prologue_tide_workbook",
            "pt",
            "Prólogo: A última página está em branco",
            "Isto não é um mapa de tesouro, mas sim um caderno de trabalho",
        ),
    ],
)
def test_regional_story_api_returns_requested_locale(
    story_id: str,
    node_id: str,
    language: str,
    expected_title: str,
    expected_caption: str,
):
    response = TestClient(app).get(f"/api/v1/stories/{story_id}?language={language}")

    assert response.status_code == 200
    overview_node = next(item for item in response.json()["nodes"] if item["id"] == node_id)
    assert overview_node["title"] == expected_title

    localized = localize_story(load_story(story_id), language)
    full_node = next(item for item in story_nodes(localized) if item["id"] == node_id)
    assert full_node["arrival_comic"][0]["caption"].startswith(expected_caption)


@pytest.mark.parametrize(
    ("language", "expected_name", "expected_text"),
    [
        (
            "zh-TW",
            "海信",
            "燈還亮著，信裡的人仍在等水路上的歸航。",
        ),
        (
            "en",
            "Sea Letter",
            "The lamp is still on, and the person in the letter is still waiting",
        ),
        (
            "pt",
            "Carta do Mar",
            "A luz continua acesa; a pessoa na carta ainda espera",
        ),
    ],
)
def test_story_session_rewards_follow_requested_locale(
    language: str,
    expected_name: str,
    expected_text: str,
):
    story = load_story("taipa_letters")
    story_session = _session(
        story_id="taipa_letters",
        current_chapter_id="chapter_taipa_bell",
    )
    story_session.state.rewards = [
        StoryReward(
            id="taipa_letter_sea",
            kind="letter",
            name="海信",
            text="灯还亮着，信里的人仍在等水路上的归航。",
        )
    ]
    service = StoryService(repository=None, trips=None)  # type: ignore[arg-type]

    response = service._response(story, story_session, language=language)

    assert response.state.rewards[0].name == expected_name
    assert response.state.rewards[0].text.startswith(expected_text)
    assert story_session.state.rewards[0].text == "灯还亮着，信里的人仍在等水路上的归航。"


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


def test_complete_coloane_workflow_awards_five_records_and_sound_postcard():
    story = load_story(COLOANE_STORY_ID)
    story_session = _session(
        story_id=COLOANE_STORY_ID,
        current_chapter_id="prologue_tide_workbook",
    )

    _complete_workflow(
        story,
        story_session,
        ending_choice_id="make_sound_postcard",
    )

    reward_ids = [reward.id for reward in story_session.state.rewards]
    stamp_ids = [
        reward.id for reward in story_session.state.rewards if reward.kind == "stamp"
    ]
    assert story_session.status == StorySessionStatus.COMPLETED
    assert story_session.state.ending_id == "make_sound_postcard"
    assert stamp_ids == [
        "record_sea",
        "record_boat",
        "record_village",
        "record_craft",
        "record_soil",
    ]
    assert reward_ids[-2:] == ["coloane_sound_postcard", "after_tide_reflection"]


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
            f"/api/v1/stories/{STORY_ID}/sessions",
            headers=owner_headers,
            params={"scheduled_day": 2, "scheduled_date": "2026-08-26"},
        )
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]
        trip_id = started.json()["trip_id"]
        assert started.json()["state"]["content_version"] == 4
        assert started.json()["state"]["scheduled_day"] == 2
        assert started.json()["state"]["scheduled_date"] == "2026-08-26"

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


def test_taipa_future_letter_is_authenticated_idempotent_and_separate_from_postcard(
    monkeypatch,
):
    client = TestClient(app)
    story = load_story(TAIPA_STORY_ID)
    owner_id = ""
    other_id = ""
    session_id = ""
    trip_id = ""
    ordinary_postcard_id = ""
    generated_calls = 0
    reflection = "愿未来的人仍能从海风、钟声和街巷里，知道这里怎样成为家。"

    def _fake_future_letter_image(**kwargs) -> bytes:
        nonlocal generated_calls
        generated_calls += 1
        assert "/qwen-image-postcard" in kwargs["prompt"]
        assert reflection not in kwargs["prompt"]
        assert kwargs["output_size"] == (900, 1600)
        buffer = BytesIO()
        Image.new("RGB", (90, 160), (55, 93, 80)).save(buffer, format="JPEG")
        return buffer.getvalue()

    monkeypatch.setattr(
        "app.features.stories.future_letter.generate_prompt_image_via_qwenpaw",
        _fake_future_letter_image,
    )

    try:
        owner_id, owner_headers = _register_headers(client, "taipa-letter-owner")
        other_id, other_headers = _register_headers(client, "taipa-letter-other")
        started = client.post(
            f"/api/v1/stories/{TAIPA_STORY_ID}/sessions",
            headers=owner_headers,
        )
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]
        trip_id = started.json()["trip_id"]

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
                    "choice_id": "send_future_taipa_letter",
                    "reflection": reflection,
                }
            progressed = client.post(
                f"/api/v1/story-sessions/{session_id}/actions",
                headers=owner_headers,
                json=payload,
            )
            assert progressed.status_code == 200, progressed.text

        ending_poi_id = next(
            str(node["poi_id"])
            for node in story_nodes(story)
            if node["kind"] == "ending"
        )
        ordinary_postcard_id = str(uuid4())
        with SessionLocal() as database:
            database.add(
                Postcard(
                    id=ordinary_postcard_id,
                    trip_id=trip_id,
                    poi_id=ending_poi_id,
                    artifact_kind="postcard",
                    stop_order=5,
                    caption="普通地点明信片",
                    caption_source="template",
                    source_type="fallback",
                    ai_generated=False,
                    language="zh-CN",
                    review_decision="pass",
                    image_svg=b'<svg data-scene-source="ai"></svg>',
                    photo_scrubbed=False,
                    created_at=datetime.now(timezone.utc),
                )
            )
            database.commit()

        metadata_path = f"/api/v1/story-sessions/{session_id}/future-letter"
        assert client.get(metadata_path, headers=owner_headers).status_code == 404
        assert client.post(metadata_path).status_code == 401
        assert client.post(metadata_path, headers=other_headers).status_code == 403

        generated = client.post(metadata_path, headers=owner_headers)
        assert generated.status_code == 201, generated.text
        future_letter = generated.json()
        assert future_letter["status"] == "ready"
        assert future_letter["scene_source"] == "ai"
        assert future_letter["reflection_truncated"] is False

        repeated = client.post(metadata_path, headers=owner_headers)
        assert repeated.status_code == 201
        assert repeated.json()["postcard_id"] == future_letter["postcard_id"]
        assert generated_calls == 1

        image_path = future_letter["image_url"]
        assert client.get(image_path).status_code == 401
        assert client.get(image_path, headers=other_headers).status_code == 403
        image = client.get(image_path, headers=owner_headers)
        assert image.status_code == 200
        assert image.headers["content-type"].startswith("image/svg+xml")
        assert b'data-artifact-kind="future_letter"' in image.content
        assert reflection.encode("utf-8") in image.content
        assert b"AI \xe5\x9c\xba\xe6\x99\xaf\xe7\xa4\xba\xe6\x84\x8f" in image.content
        assert (
            client.get(
                f"/api/v1/postcards/{future_letter['postcard_id']}/image"
            ).status_code
            == 404
        )

        listed = client.get(f"/api/v1/trips/{trip_id}/postcards")
        assert listed.status_code == 200
        assert [card["postcard_id"] for card in listed.json()["postcards"]] == [
            ordinary_postcard_id
        ]

        with SessionLocal() as database:
            database.execute(
                delete(Postcard).where(
                    Postcard.trip_id == trip_id,
                    Postcard.artifact_kind == "future_letter",
                )
            )
            database.commit()

        def _failed_future_letter_image(**_kwargs) -> bytes:
            raise SceneGenerationError("test scene failure")

        monkeypatch.setattr(
            "app.features.stories.future_letter.generate_prompt_image_via_qwenpaw",
            _failed_future_letter_image,
        )
        failed = client.post(metadata_path, headers=owner_headers)
        assert failed.status_code == 503
        restored = client.get(
            f"/api/v1/story-sessions/{session_id}", headers=owner_headers
        )
        assert restored.status_code == 200
        assert restored.json()["status"] == "completed"
        assert restored.json()["state"]["ending_reflection"] == reflection
    finally:
        if trip_id:
            with SessionLocal() as database:
                database.execute(delete(Postcard).where(Postcard.trip_id == trip_id))
                database.execute(
                    delete(StorySessionRecord).where(StorySessionRecord.id == session_id)
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
