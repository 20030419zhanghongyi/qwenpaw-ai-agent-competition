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
    with SessionLocal() as session:
        record = session.scalar(select(PostcardRecord).where(PostcardRecord.id == data["postcard_id"]))
        assert record is not None
        assert b"data:image/jpeg;base64," in record.image_svg


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
