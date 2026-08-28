"""API contract tests for privacy-scrubbed personalized postcards."""

from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.models import Postcard as PostcardRecord
from app.db.session import SessionLocal
from app.features.trips.store import trip_store
from app.main import app

client = TestClient(app)
ROUTE_ID = "photo_halfday"
USER_ID = "postcard-user"


@pytest.fixture(autouse=True)
def isolate_postcard_test_state(monkeypatch):
    monkeypatch.setattr(
        "app.features.postcards.service.review_text",
        lambda *_args, **_kwargs: {
            "decision": "pass",
            "issues": [],
            "reviewer_notes": "test stub",
            "source": "rules",
        },
    )
    trip_store.clear()
    yield
    trip_store.clear()


def _photo() -> tuple[str, bytes]:
    image = Image.new("RGB", (80, 60), color=(210, 130, 72))
    output = BytesIO()
    image.save(output, format="PNG")
    return "selfie.png", output.getvalue()


def _trip_with_checkin(user_id: str = USER_ID) -> tuple[str, str]:
    created = client.post(
        "/api/v1/trips", json={"user_id": user_id, "route_id": ROUTE_ID}
    ).json()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]
    assert (
        client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id}).status_code == 200
    )
    return trip_id, poi_id


def _create_postcard(trip_id: str, poi_id: str):
    filename, image_bytes = _photo()
    return client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN"},
        files={"photo": (filename, image_bytes, "image/png")},
    )


def test_create_postcard_for_completed_stop_and_persist_svg(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, poi_id = _trip_with_checkin()

    response = _create_postcard(trip_id, poi_id)

    assert response.status_code == 201
    data = response.json()
    assert data["trip_id"] == trip_id
    assert data["poi_id"] == poi_id
    assert data["photo_scrubbed"] is True
    assert data["caption_source"] == "template"
    assert data["ai_generated"] is False
    assert data["image_url"].startswith("/api/v1/postcards/")
    assert data["timestamp_label"]
    assert "Macau" in data["timestamp_label"] or "澳门" in data["timestamp_label"]
    assert data["geo_label"]
    assert data["task_label"]
    assert "第" in data["task_label"] or "Stop" in data["task_label"]
    assert data["route_id"] == ROUTE_ID
    assert data["latitude"] is not None
    assert data["longitude"] is not None
    with SessionLocal() as session:
        record = session.scalar(
            select(PostcardRecord).where(PostcardRecord.id == data["postcard_id"])
        )
        assert record is not None
        assert record.user_id == USER_ID
        assert b"data:image/jpeg;base64," in record.image_svg
        assert data["timestamp_label"].encode("utf-8") in record.image_svg
        assert data["geo_label"].encode("utf-8") in record.image_svg
        assert data["task_label"].encode("utf-8") in record.image_svg


def test_account_gallery_is_persisted_across_trips_and_isolated_by_user(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    first_trip, first_poi = _trip_with_checkin(USER_ID)
    second_trip, second_poi = _trip_with_checkin(USER_ID)
    other_trip, other_poi = _trip_with_checkin("other-postcard-user")

    first = _create_postcard(first_trip, first_poi)
    second = _create_postcard(second_trip, second_poi)
    other = _create_postcard(other_trip, other_poi)
    assert first.status_code == second.status_code == other.status_code == 201

    assert client.get("/api/v1/postcards").status_code == 401
    response = client.get(
        "/api/v1/postcards",
        headers={"Authorization": f"Bearer {create_access_token(USER_ID)}"},
    )

    assert response.status_code == 200
    cards = response.json()["postcards"]
    assert {card["postcard_id"] for card in cards} == {
        first.json()["postcard_id"],
        second.json()["postcard_id"],
    }
    assert {card["trip_id"] for card in cards} == {first_trip, second_trip}


def test_guest_postcard_is_claimed_when_user_signs_in(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    guest_user_id = f"guest-postcard-claim-{uuid4()}"
    trip_id, poi_id = _trip_with_checkin(guest_user_id)
    postcard = _create_postcard(trip_id, poi_id).json()
    registered = client.post(
        "/api/v1/users/register",
        json={
            "email": f"postcard-claim-{uuid4()}@test.com",
            "password": "TestPassword123!",
            "name": "Postcard Owner",
            "language": "en",
        },
    ).json()

    claimed = client.post(
        "/api/v1/users/me/claim-guest-trips",
        json={"guest_user_id": guest_user_id},
        headers={"Authorization": f"Bearer {registered['token']}"},
    )

    assert claimed.status_code == 200
    with SessionLocal() as session:
        record = session.get(PostcardRecord, postcard["postcard_id"])
        assert record is not None
        assert record.user_id == registered["user_id"]
    gallery = client.get(
        "/api/v1/postcards",
        headers={"Authorization": f"Bearer {registered['token']}"},
    ).json()["postcards"]
    assert [card["postcard_id"] for card in gallery] == [postcard["postcard_id"]]


def test_postcard_requires_checked_in_trip_stop():
    created = client.post("/api/v1/trips", json={"user_id": USER_ID, "route_id": ROUTE_ID}).json()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]

    response = _create_postcard(trip_id, poi_id)

    assert response.status_code == 422
    assert "checked in" in response.json()["detail"]


def test_postcard_scene_prewarm_queues_for_checked_in_stop(monkeypatch):
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene_via_qwenpaw",
        lambda **kwargs: (calls.append(kwargs) or (b"jpeg", None)),
    )
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards/prewarm",
        data={"poi_id": poi_id, "language": "en"},
    )

    assert response.status_code == 202
    assert response.json() == {"status": "queued", "trip_id": trip_id, "poi_id": poi_id}
    assert len(calls) == 1
    assert calls[0]["language"] == "en"


def test_postcard_scene_prewarm_requires_checked_in_stop():
    created = client.post(
        "/api/v1/trips", json={"user_id": USER_ID, "route_id": ROUTE_ID}
    ).json()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards/prewarm",
        data={"poi_id": poi_id, "language": "en"},
    )

    assert response.status_code == 422
    assert "checked in" in response.json()["detail"]


def test_postcard_is_idempotent_for_same_checked_in_stop(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, poi_id = _trip_with_checkin()

    first = _create_postcard(trip_id, poi_id)
    second = _create_postcard(trip_id, poi_id)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["postcard_id"] == first.json()["postcard_id"]


def test_legacy_postcard_is_hidden_and_can_be_replaced(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, poi_id = _trip_with_checkin()
    legacy = _create_postcard(trip_id, poi_id).json()
    with SessionLocal() as session:
        record = session.get(PostcardRecord, legacy["postcard_id"])
        assert record is not None
        record.render_version = 1
        session.commit()

    listed = client.get(f"/api/v1/trips/{trip_id}/postcards")
    assert listed.status_code == 200
    assert listed.json()["postcards"] == []
    assert client.get(legacy["image_url"]).status_code == 200

    current = _create_postcard(trip_id, poi_id)
    assert current.status_code == 201
    assert current.json()["postcard_id"] != legacy["postcard_id"]
    assert len(client.get(f"/api/v1/trips/{trip_id}/postcards").json()["postcards"]) == 1


def test_account_gallery_includes_historical_postcards(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, poi_id = _trip_with_checkin()
    postcard = _create_postcard(trip_id, poi_id).json()
    with SessionLocal() as session:
        record = session.get(PostcardRecord, postcard["postcard_id"])
        assert record is not None
        record.render_version = 1
        session.commit()

    response = client.get(
        "/api/v1/postcards",
        headers={"Authorization": f"Bearer {create_access_token(USER_ID)}"},
    )

    assert response.status_code == 200
    assert response.json()["postcards"][0]["postcard_id"] == postcard["postcard_id"]
    assert response.json()["postcards"][0]["is_historical"] is True


def test_list_postcards_follows_route_order(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, first_poi = _trip_with_checkin()
    trip = client.get(f"/api/v1/trips/{trip_id}").json()["trip"]
    second_poi = trip["stop_poi_ids"][1]
    assert (
        client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": second_poi}).status_code
        == 200
    )
    assert _create_postcard(trip_id, second_poi).status_code == 201
    assert _create_postcard(trip_id, first_poi).status_code == 201

    response = client.get(f"/api/v1/trips/{trip_id}/postcards")

    assert response.status_code == 200
    assert [card["poi_id"] for card in response.json()["postcards"]] == [first_poi, second_poi]


def test_postcard_image_is_delivered_as_svg(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, poi_id = _trip_with_checkin()
    postcard = _create_postcard(trip_id, poi_id).json()

    response = client.get(postcard["image_url"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content


def test_postcard_png_is_delivered_as_download(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    trip_id, poi_id = _trip_with_checkin()
    postcard = _create_postcard(trip_id, poi_id).json()

    response = client.get(f"/api/v1/postcards/{postcard['postcard_id']}/image.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["content-disposition"].startswith("attachment;")
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == "PNG"
        assert image.size == (1200, 800)


def test_postcard_svg_constrains_long_right_column_text():
    from app.features.postcards.service import _render_svg

    image = _render_svg(
        photo_jpeg=b"jpeg",
        scene_svg=None,
        poi_name="Hong Kong-Zhuhai-Macao Bridge Macao Port",
        caption="A long but safe postcard caption for this stop.",
        timestamp_label="2026-08-24 11:00 · Macau",
        geo_label="22.192°N 113.542°E · St. Lawrence Parish",
        task_label="Stop 9 of 9 · Macau cultural discovery itinerary",
        scene_source="ai",
    )

    assert image.count(b'<foreignObject x="842"') == 4
    assert b'width="270"' in image
    assert image.count(b"overflow-wrap:anywhere") == 3
    assert b"overflow-wrap:break-word" in image
    assert b'y="228" width="270" height="132"' in image
    assert b'y="374" width="270" height="152"' in image
    assert b"font: 24px 'Noto Serif CJK SC'" in image


def test_postcard_image_upgrades_legacy_text_layout():
    from app.features.postcards.service import _normalize_postcard_svg_layout

    legacy = b'''<svg>
      <foreignObject x="842" y="228" width="270" height="70"><div style="font: 28px 'Noto Serif CJK SC', 'Songti SC', serif; line-height:1.08">Long title</div></foreignObject>
      <foreignObject x="842" y="318" width="270" height="200"><div style="font: 27px 'Noto Serif CJK SC', serif">Caption</div></foreignObject>
    </svg>'''

    upgraded = _normalize_postcard_svg_layout(legacy)

    assert b'y="228" width="270" height="132"' in upgraded
    assert b'y="374" width="270" height="152"' in upgraded
    assert b"font: 24px 'Noto Serif CJK SC'" in upgraded
    assert b"font: 21px 'Noto Serif CJK SC'" in upgraded


def test_postcard_rejects_non_image_upload():
    trip_id, poi_id = _trip_with_checkin()
    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id},
        files={"photo": ("not-image.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 422
    assert "valid image" in response.json()["detail"]


def test_postcard_styles_scrubbed_user_photo(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    _filename, styled = _photo()

    def _style(**kwargs):
        assert kwargs["style"] == "watercolor"
        assert kwargs["photo_jpeg"].startswith(b"\xff\xd8")
        return styled

    monkeypatch.setattr(
        "app.features.postcards.service.stylize_photo_via_qwenpaw",
        _style,
    )
    trip_id, poi_id = _trip_with_checkin()
    filename, photo = _photo()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN", "photo_style": "watercolor"},
        files={"photo": (filename, photo, "image/png")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["scene_source"] == "ai_edit"
    assert data["photo_style"] == "watercolor"
    assert data["has_user_photo"] is True
    assert data["photo_scrubbed"] is True
    image = client.get(data["image_url"])
    assert b'data-scene-source="ai_edit"' in image.content
    assert b'data-photo-style="watercolor"' in image.content


def test_postcard_photo_style_failure_keeps_scrubbed_original(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr(
        "app.features.postcards.service.stylize_photo_via_qwenpaw",
        lambda **_: None,
    )
    trip_id, poi_id = _trip_with_checkin()
    filename, photo = _photo()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "photo_style": "souvenir"},
        files={"photo": (filename, photo, "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["scene_source"] == "user"
    assert response.json()["photo_style"] is None


def test_postcard_rejects_photo_style_without_photo():
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "photo_style": "ink"},
    )

    assert response.status_code == 422
    assert "requires an uploaded photo" in response.json()["detail"]


def test_postcard_rejects_unknown_photo_style():
    trip_id, poi_id = _trip_with_checkin()
    filename, photo = _photo()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "photo_style": "cyberpunk"},
        files={"photo": (filename, photo, "image/png")},
    )

    assert response.status_code == 422
    assert "unsupported photo style" in response.json()["detail"]


def test_postcard_default_no_photo_requires_scene_agent(monkeypatch):
    seen = {"ai_scene": None}

    def _track(**kwargs):
        seen["ai_scene"] = kwargs.get("ai_scene")
        return ("ai", _photo()[1], None)

    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr("app.features.postcards.service.generate_ai_scene", _track)
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN"},
    )

    assert response.status_code == 201
    data = response.json()
    assert seen["ai_scene"] is True
    assert data["scene_source"] == "ai"
    assert data["has_user_photo"] is False
    image = client.get(data["image_url"])
    assert image.status_code == 200
    assert b'data-scene-source="ai"' in image.content


def test_no_photo_scene_is_reused_for_same_poi_across_users(monkeypatch):
    from app.features.postcards.service import postcard_service

    calls = 0
    test_trip_ids: set[str] = set()
    original_candidates = postcard_service._repository.list_reusable_scene_candidates

    def _test_candidates(poi_id: str, limit: int = 10):
        return [
            record
            for record in original_candidates(poi_id, limit)
            if record.trip_id in test_trip_ids
        ]

    def _generate(**_kwargs):
        nonlocal calls
        calls += 1
        return "ai", _photo()[1], None

    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr("app.features.postcards.service.generate_ai_scene", _generate)
    monkeypatch.setattr(
        postcard_service._repository,
        "list_reusable_scene_candidates",
        _test_candidates,
    )
    first_trip, first_poi = _trip_with_checkin("postcard-cache-user-one")
    second_trip, second_poi = _trip_with_checkin("postcard-cache-user-two")
    test_trip_ids.update((first_trip, second_trip))
    assert first_poi == second_poi

    first = client.post(
        f"/api/v1/trips/{first_trip}/postcards",
        data={"poi_id": first_poi, "language": "zh-CN"},
    )
    second = client.post(
        f"/api/v1/trips/{second_trip}/postcards",
        data={"poi_id": second_poi, "language": "en"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert calls == 1
    assert first.json()["postcard_id"] != second.json()["postcard_id"]


def test_user_upload_is_never_reused_as_shared_poi_scene(monkeypatch):
    from app.features.postcards.service import postcard_service

    calls = 0
    test_trip_ids: set[str] = set()
    original_candidates = postcard_service._repository.list_reusable_scene_candidates

    def _test_candidates(poi_id: str, limit: int = 10):
        return [
            record
            for record in original_candidates(poi_id, limit)
            if record.trip_id in test_trip_ids
        ]

    def _generate(**_kwargs):
        nonlocal calls
        calls += 1
        return "ai", _photo()[1], None

    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr("app.features.postcards.service.generate_ai_scene", _generate)
    monkeypatch.setattr(
        postcard_service._repository,
        "list_reusable_scene_candidates",
        _test_candidates,
    )
    upload_trip, upload_poi = _trip_with_checkin("postcard-private-upload-user")
    shared_trip, shared_poi = _trip_with_checkin("postcard-shared-scene-user")
    test_trip_ids.update((upload_trip, shared_trip))
    assert upload_poi == shared_poi

    assert _create_postcard(upload_trip, upload_poi).status_code == 201
    generated = client.post(
        f"/api/v1/trips/{shared_trip}/postcards",
        data={"poi_id": shared_poi, "language": "en"},
    )

    assert generated.status_code == 201
    assert generated.json()["has_user_photo"] is False
    assert calls == 1


def test_english_postcard_stamps_do_not_leak_chinese(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene",
        lambda **_: ("ai", _photo()[1], None),
    )
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "en"},
    )

    assert response.status_code == 201
    data = response.json()
    for value in (data["poi_name"], data["geo_label"], data["route_name"], data["task_label"]):
        assert not any("\u3400" <= character <= "\u9fff" for character in (value or ""))


def test_postcard_ai_scene_request(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 720">'
        '<rect width="960" height="720" fill="#7eb6c9"/>'
        "</svg>"
    )

    def _ai(**kwargs):
        assert kwargs.get("ai_scene") is True
        return ("ai", None, svg)

    monkeypatch.setattr("app.features.postcards.service.generate_ai_scene", _ai)
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN", "ai_scene": "true"},
    )

    assert response.status_code == 201
    assert response.json()["scene_source"] == "ai"


def test_postcard_scene_failure_returns_503_without_persisting(monkeypatch):
    from app.features.postcards.scene_image import SceneGenerationError

    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)

    def _fail(**_kwargs):
        raise SceneGenerationError("invalid image key")

    monkeypatch.setattr("app.features.postcards.service.generate_ai_scene", _fail)
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "en"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "POSTCARD_SCENE_UNAVAILABLE"
    assert client.get(f"/api/v1/trips/{trip_id}/postcards").json()["postcards"] == []


def test_postcard_uses_ai_scene_when_available(monkeypatch):
    from io import BytesIO

    from PIL import Image

    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    buf = BytesIO()
    Image.new("RGB", (320, 240), (40, 120, 110)).save(buf, format="JPEG")
    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene",
        lambda **_: ("ai", buf.getvalue(), None),
    )
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN", "ai_scene": "true"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["scene_source"] == "ai"
    assert data["has_user_photo"] is False
    image = client.get(data["image_url"])
    assert b"AI scene" not in image.content
    assert b'data-scene-source="ai"' in image.content


def test_postcard_embeds_qwenpaw_svg_scene(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 720">'
        '<rect width="960" height="720" fill="#7eb6c9"/>'
        '<rect x="200" y="300" width="400" height="200" fill="#3d4f4c"/>'
        "</svg>"
    )
    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene",
        lambda **_: ("ai", None, svg),
    )
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN", "ai_scene": "true"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["scene_source"] == "ai"
    image = client.get(data["image_url"])
    assert b'fill="#7eb6c9"' in image.content
    assert b"AI scene" not in image.content
    assert b'data-scene-source="ai"' in image.content


def test_postcard_can_be_deleted(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene",
        lambda **_: ("ai", _photo()[1], None),
    )
    trip_id, poi_id = _trip_with_checkin()
    created = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN"},
    ).json()
    postcard_id = created["postcard_id"]

    deleted = client.delete(f"/api/v1/postcards/{postcard_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/postcards/{postcard_id}/image").status_code == 404
    listed = client.get(f"/api/v1/trips/{trip_id}/postcards").json()["postcards"]
    assert listed == []


def test_postcard_replace_creates_new_id(monkeypatch):
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    reuse_cached: list[bool] = []

    def _generate(**kwargs):
        reuse_cached.append(kwargs["reuse_cached"])
        return "ai", _photo()[1], None

    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene",
        _generate,
    )
    trip_id, poi_id = _trip_with_checkin()
    first = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN"},
    ).json()
    second = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN", "replace": "true"},
    ).json()

    assert second["postcard_id"] != first["postcard_id"]
    assert client.get(first["image_url"]).status_code == 404
    assert client.get(second["image_url"]).status_code == 200
    listed = client.get(f"/api/v1/trips/{trip_id}/postcards").json()["postcards"]
    assert len(listed) == 1
    assert listed[0]["postcard_id"] == second["postcard_id"]
    assert reuse_cached == [True, False]
