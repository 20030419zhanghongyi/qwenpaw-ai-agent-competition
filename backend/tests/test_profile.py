"""API tests for personal profile trip history, favorites, and feedback."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Favorite as FavoriteRecord
from app.db.models import TripFeedback as FeedbackRecord
from app.db.models import User as UserRecord
from app.db.models.user import DEFAULT_GUEST_USER_NAME, guest_user_email
from app.db.session import SessionLocal
from app.features.profile.store import profile_store
from app.features.trips.store import trip_store
from app.main import app

client = TestClient(app)
USER_ID = "demo-user-001"
OTHER_USER_ID = "demo-user-002"
ROUTE_ID = "photo_halfday"
POI_ID = "poi_senado"
SECOND_POI_ID = "poi_paixao"


@pytest.fixture(autouse=True)
def clear_stores():
    profile_store.clear()
    trip_store.clear()
    yield
    profile_store.clear()
    trip_store.clear()


def create_trip(user_id: str = USER_ID) -> dict:
    response = client.post(
        "/api/v1/trips",
        json={"user_id": user_id, "route_id": ROUTE_ID},
    )
    assert response.status_code == 201
    return response.json()


def complete_trip(user_id: str = USER_ID) -> dict:
    created = create_trip(user_id)
    trip_id = created["trip"]["trip_id"]
    completed = created
    for poi_id in created["trip"]["stop_poi_ids"]:
        response = client.post(
            f"/api/v1/trips/{trip_id}/checkins",
            json={"poi_id": poi_id},
        )
        assert response.status_code == 200
        completed = response.json()
    return completed


def feedback_payload(**overrides) -> dict:
    payload = {
        "user_id": USER_ID,
        "rating": 5,
        "comment": "  Route was comfortable.  ",
        "route_reasonable": True,
        "walking_comfortable": True,
    }
    payload.update(overrides)
    return payload


def test_empty_trip_history_returns_list():
    response = client.get(f"/api/v1/users/{USER_ID}/trips")
    assert response.status_code == 200
    assert response.json() == []


def test_trip_history_returns_active_and_completed():
    create_trip()
    complete_trip()
    response = client.get(f"/api/v1/users/{USER_ID}/trips")
    assert {item["status"] for item in response.json()} == {"active", "completed"}


def test_trip_history_is_newest_first():
    first = create_trip()
    second = create_trip()
    response = client.get(f"/api/v1/users/{USER_ID}/trips")
    assert [item["trip_id"] for item in response.json()] == [
        second["trip"]["trip_id"],
        first["trip"]["trip_id"],
    ]


def test_trip_history_status_filter():
    active = create_trip()
    complete_trip()
    response = client.get(f"/api/v1/users/{USER_ID}/trips?status=active")
    assert response.status_code == 200
    assert [item["trip_id"] for item in response.json()] == [active["trip"]["trip_id"]]


def test_trip_history_limit():
    create_trip()
    create_trip()
    response = client.get(f"/api/v1/users/{USER_ID}/trips?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_trip_history_contains_progress():
    created = create_trip()
    poi_id = created["trip"]["stop_poi_ids"][0]
    client.post(
        f"/api/v1/trips/{created['trip']['trip_id']}/checkins",
        json={"poi_id": poi_id},
    )
    item = client.get(f"/api/v1/users/{USER_ID}/trips").json()[0]
    assert item["total_stops"] == 5
    assert item["completed_stops"] == 1
    assert item["completion_ratio"] == 0.2


def test_add_valid_favorite():
    response = client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    assert response.status_code == 201
    assert response.json()["poi_id"] == POI_ID


def test_add_favorite_creates_guest_user_with_default_name():
    guest_user_id = "guest-favorite-user"

    response = client.post(f"/api/v1/users/{guest_user_id}/favorites/pois/{POI_ID}")

    assert response.status_code == 201
    with SessionLocal() as session:
        guest = session.get(UserRecord, guest_user_id)
        assert guest is not None
        assert guest.name == DEFAULT_GUEST_USER_NAME
        assert guest.email == guest_user_email(guest_user_id)


def test_favorite_is_persisted_in_database():
    response = client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    assert response.status_code == 201
    with SessionLocal() as session:
        record = session.scalar(
            select(FavoriteRecord).where(
                FavoriteRecord.user_id == USER_ID,
                FavoriteRecord.poi_id == POI_ID,
            )
        )
        assert record is not None


def test_add_unknown_favorite_returns_404():
    response = client.post(f"/api/v1/users/{USER_ID}/favorites/pois/missing-poi")
    assert response.status_code == 404
    with SessionLocal() as session:
        favorite = session.scalar(
            select(FavoriteRecord).where(
                FavoriteRecord.user_id == USER_ID,
                FavoriteRecord.poi_id == "missing-poi",
            )
        )
        assert favorite is None


def test_add_favorite_is_idempotent():
    first = client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    second = client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()


def test_list_favorites():
    client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    response = client.get(f"/api/v1/users/{USER_ID}/favorites/pois")
    assert response.status_code == 200
    assert [item["poi_id"] for item in response.json()] == [POI_ID]


def test_favorite_contains_poi_display_fields():
    client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    favorite = client.get(f"/api/v1/users/{USER_ID}/favorites/pois").json()[0]
    assert favorite["poi_name"]
    assert isinstance(favorite["longitude"], float)
    assert isinstance(favorite["latitude"], float)
    assert favorite["created_at"]


def test_remove_favorite():
    client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    response = client.delete(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/users/{USER_ID}/favorites/pois").json() == []


def test_remove_favorite_deletes_database_record():
    client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    response = client.delete(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    assert response.status_code == 204
    with SessionLocal() as session:
        record = session.scalar(
            select(FavoriteRecord).where(
                FavoriteRecord.user_id == USER_ID,
                FavoriteRecord.poi_id == POI_ID,
            )
        )
        assert record is None


def test_remove_favorite_is_idempotent():
    first = client.delete(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    second = client.delete(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    assert first.status_code == second.status_code == 204


def test_favorites_are_isolated_by_user():
    client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    client.post(f"/api/v1/users/{OTHER_USER_ID}/favorites/pois/{SECOND_POI_ID}")
    first = client.get(f"/api/v1/users/{USER_ID}/favorites/pois").json()
    second = client.get(f"/api/v1/users/{OTHER_USER_ID}/favorites/pois").json()
    assert [item["poi_id"] for item in first] == [POI_ID]
    assert [item["poi_id"] for item in second] == [SECOND_POI_ID]


def test_submit_feedback_for_completed_trip():
    trip_id = complete_trip()["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    )
    assert response.status_code == 201
    assert response.json()["comment"] == "Route was comfortable."


def test_feedback_is_persisted_in_database():
    trip_id = complete_trip()["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    )
    assert response.status_code == 201
    with SessionLocal() as session:
        record = session.scalar(
            select(FeedbackRecord).where(FeedbackRecord.trip_id == trip_id)
        )
        assert record is not None
        assert record.rating == 5


def test_active_trip_rejects_feedback():
    trip_id = create_trip()["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    )
    assert response.status_code == 409


def test_feedback_rejects_wrong_user():
    trip_id = complete_trip()["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(user_id=OTHER_USER_ID),
    )
    assert response.status_code == 403


def test_feedback_rejects_rating_below_one():
    trip_id = complete_trip()["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(rating=0),
    )
    assert response.status_code == 422


def test_feedback_rejects_rating_above_five():
    trip_id = complete_trip()["trip"]["trip_id"]
    response = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(rating=6),
    )
    assert response.status_code == 422


def test_get_feedback():
    trip_id = complete_trip()["trip"]["trip_id"]
    created = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    )
    response = client.get(f"/api/v1/trips/{trip_id}/feedback")
    assert response.status_code == 200
    assert response.json() == created.json()


def test_get_missing_feedback_returns_404():
    trip_id = create_trip()["trip"]["trip_id"]
    response = client.get(f"/api/v1/trips/{trip_id}/feedback")
    assert response.status_code == 404


def test_repeated_feedback_updates_original():
    trip_id = complete_trip()["trip"]["trip_id"]
    first = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    )
    second = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(rating=4, comment="Updated"),
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["feedback_id"] == first.json()["feedback_id"]
    assert second.json()["rating"] == 4
    assert second.json()["comment"] == "Updated"


def test_feedback_update_changes_database_record():
    trip_id = complete_trip()["trip"]["trip_id"]
    first = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    ).json()
    second = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(rating=4, comment="Updated in database"),
    ).json()
    with SessionLocal() as session:
        record = session.scalar(
            select(FeedbackRecord).where(FeedbackRecord.trip_id == trip_id)
        )
        assert record is not None
        assert record.id == first["feedback_id"] == second["feedback_id"]
        assert record.rating == 4
        assert record.comment == "Updated in database"
        assert record.created_at.isoformat().replace("+00:00", "Z") == first["created_at"]
        assert record.updated_at.isoformat().replace("+00:00", "Z") == second["updated_at"]


def test_feedback_update_preserves_created_at_and_changes_updated_at():
    trip_id = complete_trip()["trip"]["trip_id"]
    first = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(),
    ).json()
    second = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json=feedback_payload(rating=4),
    ).json()
    assert second["created_at"] == first["created_at"]
    assert second["updated_at"] > first["updated_at"]
