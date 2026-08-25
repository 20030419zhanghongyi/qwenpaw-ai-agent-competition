"""API contract tests for privacy-scrubbed personalized postcards."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

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


def _trip_with_checkin() -> tuple[str, str]:
    created = client.post("/api/v1/trips", json={"user_id": USER_ID, "route_id": ROUTE_ID}).json()
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
        assert b"data:image/jpeg;base64," in record.image_svg
        assert data["timestamp_label"].encode("utf-8") in record.image_svg
        assert data["geo_label"].encode("utf-8") in record.image_svg
        assert data["task_label"].encode("utf-8") in record.image_svg


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
    monkeypatch.setattr(
        "app.features.postcards.service.generate_ai_scene",
        lambda **_: ("ai", _photo()[1], None),
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
