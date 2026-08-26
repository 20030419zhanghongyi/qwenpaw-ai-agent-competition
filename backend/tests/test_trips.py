"""API tests for Demo trip, check-in, and progress state."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Checkin as CheckinRecord
from app.db.models import Trip as TripRecord
from app.db.models import User as UserRecord
from app.db.models.user import DEFAULT_GUEST_USER_NAME, guest_user_email
from app.db.session import SessionLocal
from app.features.trips.store import trip_store
from app.main import app

client = TestClient(app)
ROUTE_ID = "photo_halfday"
USER_ID = "demo-user-001"


@pytest.fixture(autouse=True)
def clear_trip_store():
    trip_store.clear()
    yield
    trip_store.clear()


def create_trip(user_id: str = USER_ID) -> dict:
    response = client.post(
        "/api/v1/trips",
        json={"user_id": user_id, "route_id": ROUTE_ID},
    )
    assert response.status_code == 201
    return response.json()


def test_create_valid_trip():
    data = create_trip()
    assert data["trip"]["user_id"] == USER_ID
    assert data["trip"]["route_id"] == ROUTE_ID
    assert data["trip"]["status"] == "active"
    assert data["trip"]["stop_poi_ids"] == [
        "poi_0002",
        "poi_0001",
        "poi_0003",
        "poi_0018",
        "poi_0030",
    ]
    assert data["trip"]["checked_in_poi_ids"] == []


def test_created_trip_is_persisted_in_database():
    data = create_trip()
    with SessionLocal() as session:
        record = session.get(TripRecord, data["trip"]["trip_id"])
        assert record is not None
        assert record.user_id == USER_ID
        assert record.route_id == ROUTE_ID


def test_create_trip_creates_guest_user_with_default_name():
    guest_user_id = "guest-trip-user"

    create_trip(guest_user_id)

    with SessionLocal() as session:
        guest = session.get(UserRecord, guest_user_id)
        assert guest is not None
        assert guest.name == DEFAULT_GUEST_USER_NAME
        assert guest.email == guest_user_email(guest_user_id)


def test_authenticated_user_can_claim_guest_trips():
    guest_user_id = "guest-claim-test"
    created = create_trip(guest_user_id)
    registered = client.post(
        "/api/v1/users/register",
        json={
            "email": f"claim-trip-{uuid4()}@test.com",
            "password": "TestPassword123!",
            "name": "Trip Owner",
            "language": "en",
        },
    )
    assert registered.status_code == 201, registered.text
    account = registered.json()

    claimed = client.post(
        "/api/v1/users/me/claim-guest-trips",
        json={"guest_user_id": guest_user_id},
        headers={"Authorization": f"Bearer {account['token']}"},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json() == {"claimed_trips": 1}

    with SessionLocal() as session:
        record = session.get(TripRecord, created["trip"]["trip_id"])
        assert record is not None
        assert record.user_id == account["user_id"]

    repeated = client.post(
        "/api/v1/users/me/claim-guest-trips",
        json={"guest_user_id": guest_user_id},
        headers={"Authorization": f"Bearer {account['token']}"},
    )
    assert repeated.status_code == 200
    assert repeated.json() == {"claimed_trips": 0}


def test_claim_guest_trips_rejects_regular_user_id():
    registered = client.post(
        "/api/v1/users/register",
        json={
            "email": f"claim-reject-{uuid4()}@test.com",
            "password": "TestPassword123!",
            "name": "Trip Owner",
            "language": "en",
        },
    ).json()
    response = client.post(
        "/api/v1/users/me/claim-guest-trips",
        json={"guest_user_id": "ordinary-user"},
        headers={"Authorization": f"Bearer {registered['token']}"},
    )
    assert response.status_code == 422


def test_create_trip_with_custom_stop_poi_ids():
    """Adjusted walk nodes can override the static template stop list."""
    custom_stops = ["poi_0020", "poi_0001", "poi_0003"]
    response = client.post(
        "/api/v1/trips",
        json={
            "user_id": USER_ID,
            "route_id": ROUTE_ID,
            "stop_poi_ids": custom_stops,
        },
    )
    assert response.status_code == 201
    trip = response.json()["trip"]
    assert trip["route_id"] == ROUTE_ID
    assert trip["stop_poi_ids"] == custom_stops

    checkin = client.post(
        f"/api/v1/trips/{trip['trip_id']}/checkins",
        json={"poi_id": "poi_0020"},
    )
    assert checkin.status_code == 200
    assert checkin.json()["trip"]["checked_in_poi_ids"] == ["poi_0020"]


def test_simulate_arrive_style_rebuild_then_checkin_poi_outside_template():
    """Regression: create with walk stops that insert a POI absent from the template."""
    # photo_halfday template does not start with poi_0020; custom list must win.
    response = client.post(
        "/api/v1/trips",
        json={
            "user_id": f"{USER_ID}-rebuild",
            "route_id": ROUTE_ID,
            "stop_poi_ids": ["poi_0020", "poi_0002", "poi_0001"],
        },
    )
    assert response.status_code == 201
    trip = response.json()["trip"]
    assert "poi_0020" in trip["stop_poi_ids"]
    assert trip["stop_poi_ids"][0] == "poi_0020"

    checkin = client.post(
        f"/api/v1/trips/{trip['trip_id']}/checkins",
        json={"poi_id": "poi_0020"},
    )
    assert checkin.status_code == 200
    assert checkin.json()["trip"]["checked_in_poi_ids"] == ["poi_0020"]


def test_create_trip_rejects_empty_custom_stop_poi_ids():
    response = client.post(
        "/api/v1/trips",
        json={"user_id": USER_ID, "route_id": ROUTE_ID, "stop_poi_ids": []},
    )
    assert response.status_code == 422
    assert "stop_poi_ids" in response.json()["detail"]


def test_create_trip_with_unknown_route_returns_404():
    response = client.post(
        "/api/v1/trips",
        json={"user_id": USER_ID, "route_id": "missing-route"},
    )
    assert response.status_code == 404
    assert "Route not found" in response.json()["detail"]


def test_create_trip_rejects_route_with_unknown_poi(monkeypatch):
    monkeypatch.setattr(
        "app.features.trips.service.get_template",
        lambda route_id: {
            "template_id": route_id,
            "nodes": [{"poi_id": "missing-poi", "order": 1}],
        },
    )
    response = client.post(
        "/api/v1/trips",
        json={"user_id": USER_ID, "route_id": "invalid-poi-route"},
    )
    assert response.status_code == 422
    assert "Route references unknown POIs: missing-poi" in response.json()["detail"]


def test_get_trip():
    created = create_trip()
    response = client.get(f"/api/v1/trips/{created['trip']['trip_id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_trip_returns_404():
    response = client.get("/api/v1/trips/missing-trip")
    assert response.status_code == 404


def test_get_current_trip():
    created = create_trip()
    response = client.get(f"/api/v1/users/{USER_ID}/current-trip")
    assert response.status_code == 200
    assert response.json()["trip"]["trip_id"] == created["trip"]["trip_id"]


def test_get_current_trip_returns_404_when_user_has_no_active_trip():
    response = client.get("/api/v1/users/no-active-trip/current-trip")
    assert response.status_code == 404


def test_first_checkin_succeeds():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]
    response = client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id})
    assert response.status_code == 200
    assert response.json()["trip"]["checked_in_poi_ids"] == [poi_id]


def test_checkin_is_persisted_in_database():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]
    response = client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id})
    assert response.status_code == 200
    with SessionLocal() as session:
        records = session.scalars(
            select(CheckinRecord).where(CheckinRecord.trip_id == trip_id)
        ).all()
        assert [record.poi_id for record in records] == [poi_id]


def test_duplicate_checkin_is_idempotent():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]
    first = client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id})
    second = client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id})
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert second.json()["trip"]["checked_in_poi_ids"] == [poi_id]


def test_checkin_rejects_poi_outside_trip():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/checkins",
        json={"poi_id": "poi_senado"},
    )
    assert response.status_code == 422
    assert "not part of trip" in response.json()["detail"]


def test_progress_is_calculated():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    first_poi, second_poi = created["trip"]["stop_poi_ids"][:2]
    client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": first_poi})
    response = client.get(f"/api/v1/trips/{trip_id}/progress")
    assert response.status_code == 200
    assert response.json() == {
        "total_stops": 5,
        "completed_stops": 1,
        "completion_ratio": 0.2,
        "next_poi_id": second_poi,
    }


def test_last_checkin_completes_trip():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    response = None
    for poi_id in created["trip"]["stop_poi_ids"]:
        response = client.post(
            f"/api/v1/trips/{trip_id}/checkins",
            json={"poi_id": poi_id},
        )
    assert response is not None
    assert response.json()["trip"]["status"] == "completed"
    assert response.json()["progress"] == {
        "total_stops": 5,
        "completed_stops": 5,
        "completion_ratio": 1.0,
        "next_poi_id": None,
    }


def test_completed_trip_is_not_returned_as_current_trip():
    created = create_trip()
    trip_id = created["trip"]["trip_id"]
    for poi_id in created["trip"]["stop_poi_ids"]:
        client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id})
    response = client.get(f"/api/v1/users/{USER_ID}/current-trip")
    assert response.status_code == 404
