"""API tests for Demo trip, check-in, and progress state."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Checkin as CheckinRecord
from app.db.models import Trip as TripRecord
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
        "poi_paixao",
        "poi_ruins_st_paul",
        "poi_mount_fortress",
        "poi_fatong",
        "poi_sv_lazaro",
    ]
    assert data["trip"]["checked_in_poi_ids"] == []


def test_created_trip_is_persisted_in_database():
    data = create_trip()
    with SessionLocal() as session:
        record = session.get(TripRecord, data["trip"]["trip_id"])
        assert record is not None
        assert record.user_id == USER_ID
        assert record.route_id == ROUTE_ID


def test_create_trip_with_unknown_route_returns_404():
    response = client.post(
        "/api/v1/trips",
        json={"user_id": USER_ID, "route_id": "missing-route"},
    )
    assert response.status_code == 404
    assert "Route not found" in response.json()["detail"]


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
