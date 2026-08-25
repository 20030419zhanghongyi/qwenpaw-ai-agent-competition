"""Personal memoir ownership, factual source, photo, and share privacy contracts."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.features.trips.store import trip_store
from app.main import app

client = TestClient(app)
USER_ID = "memoir-test-user"
ROUTE_ID = "photo_halfday"


@pytest.fixture(autouse=True)
def clear_created_trips():
    trip_store.clear()
    yield
    trip_store.clear()


def _headers(user_id: str = USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _checked_in_trip() -> dict:
    created = client.post(
        "/api/v1/trips", json={"user_id": USER_ID, "route_id": ROUTE_ID}
    )
    assert created.status_code == 201, created.text
    trip = created.json()["trip"]
    checkin = client.post(
        f"/api/v1/trips/{trip['trip_id']}/checkins",
        json={"poi_id": trip["stop_poi_ids"][0]},
    )
    assert checkin.status_code == 200, checkin.text
    return checkin.json()["trip"]


def test_memoir_requires_authentication_and_trip_owner():
    trip = _checked_in_trip()
    url = f"/api/v1/trips/{trip['trip_id']}/memoir"
    assert client.post(url, json={"style": "diary"}).status_code == 401
    forbidden = client.post(
        url, json={"style": "diary"}, headers=_headers("another-user")
    )
    assert forbidden.status_code == 403


def test_create_memoir_uses_checkin_order_and_is_idempotent():
    trip = _checked_in_trip()
    url = f"/api/v1/trips/{trip['trip_id']}/memoir"
    first = client.post(
        url, json={"style": "documentary", "language": "zh-CN"}, headers=_headers()
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["style"] == "documentary"
    assert [chapter["poi_id"] for chapter in body["chapters"]] == trip["checked_in_poi_ids"]
    repeated = client.post(url, json={"style": "social"}, headers=_headers())
    assert repeated.status_code == 201
    assert repeated.json()["memoir_id"] == body["memoir_id"]


def test_share_privacy_filters_people_date_route_and_notes_then_revokes():
    trip = _checked_in_trip()
    created = client.post(
        f"/api/v1/trips/{trip['trip_id']}/memoir",
        json={"style": "diary", "language": "zh-CN"},
        headers=_headers(),
    ).json()
    chapter = {**created["chapters"][0], "personal_note": "private note"}
    updated = client.put(
        f"/api/v1/memoirs/{created['memoir_id']}",
        json={"chapters": [chapter]},
        headers=_headers(),
    )
    assert updated.status_code == 200, updated.text

    photo = client.post(
        f"/api/v1/memoirs/{created['memoir_id']}/photos",
        files={"photo": ("people.png", b"small-image", "image/png")},
        data={"poi_id": chapter["poi_id"], "has_people": "true"},
        headers=_headers(),
    )
    assert photo.status_code == 201, photo.text

    share = client.post(
        f"/api/v1/memoirs/{created['memoir_id']}/shares",
        json={
            "hide_people_photos": True,
            "hide_date": True,
            "hide_exact_route": True,
            "hide_personal_notes": True,
        },
        headers=_headers(),
    )
    assert share.status_code == 201, share.text
    token = share.json()["token"]
    public = client.get(f"/api/v1/shared/memoirs/{token}")
    assert public.status_code == 200, public.text
    public_body = public.json()
    assert public_body["travel_date"] is None
    assert public_body["route_id"] is None
    assert public_body["photos"] == []
    assert public_body["chapters"][0]["personal_note"] == ""

    revoked = client.delete(
        f"/api/v1/memoirs/{created['memoir_id']}/shares", headers=_headers()
    )
    assert revoked.status_code == 204
    assert client.get(f"/api/v1/shared/memoirs/{token}").status_code == 404
