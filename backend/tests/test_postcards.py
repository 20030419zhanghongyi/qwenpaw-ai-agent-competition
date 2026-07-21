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
def clear_trip_store():
    trip_store.clear()
    yield
    trip_store.clear()


def _photo() -> tuple[str, bytes]:
    image = Image.new("RGB", (80, 60), color=(210, 130, 72))
    output = BytesIO()
    image.save(output, format="PNG")
    return "selfie.png", output.getvalue()


def _trip_with_checkin() -> tuple[str, str]:
    created = client.post(
        "/api/v1/trips", json={"user_id": USER_ID, "route_id": ROUTE_ID}
    ).json()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]
    assert client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id}).status_code == 200
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
        record = session.scalar(select(PostcardRecord).where(PostcardRecord.id == data["postcard_id"]))
        assert record is not None
        assert b"data:image/jpeg;base64," in record.image_svg
        assert data["timestamp_label"].encode("utf-8") in record.image_svg
        assert data["geo_label"].encode("utf-8") in record.image_svg
        assert data["task_label"].encode("utf-8") in record.image_svg


def test_postcard_requires_checked_in_trip_stop():
    created = client.post(
        "/api/v1/trips", json={"user_id": USER_ID, "route_id": ROUTE_ID}
    ).json()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]

    response = _create_postcard(trip_id, poi_id)

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
    assert client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": second_poi}).status_code == 200
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


def test_postcard_rejects_non_image_upload():
    trip_id, poi_id = _trip_with_checkin()
    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id},
        files={"photo": ("not-image.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 422
    assert "valid image" in response.json()["detail"]


def test_postcard_default_no_photo_is_instant_local_scene(monkeypatch):
    """Default create uses local scenic art; AI scene is opt-in."""
    seen = {"ai_scene": None}

    def _track(**kwargs):
        seen["ai_scene"] = kwargs.get("ai_scene")
        if not kwargs.get("ai_scene"):
            return ("", None, None)
        return ("ai", None, "<svg viewBox='0 0 1 1'></svg>")

    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)
    monkeypatch.setattr("app.features.postcards.service.generate_ai_scene", _track)
    trip_id, poi_id = _trip_with_checkin()

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN"},
    )

    assert response.status_code == 201
    data = response.json()
    assert seen["ai_scene"] is False
    assert data["scene_source"] == "placeholder"
    assert data["has_user_photo"] is False
    image = client.get(data["image_url"])
    assert image.status_code == 200
    assert b'data-scene-source="placeholder"' in image.content


def test_postcard_ai_scene_opt_in(monkeypatch):
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
        lambda **_: ("", None, None),
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
        lambda **_: ("", None, None),
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
