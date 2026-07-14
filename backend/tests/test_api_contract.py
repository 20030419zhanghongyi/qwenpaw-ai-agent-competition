"""Stable API contracts for backend handoff consumers."""

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.features.profile.store import profile_store
from app.features.trips.store import trip_store
from app.main import app

client = TestClient(app)
USER_ID = "contract-user"
ROUTE_ID = "photo_halfday"
POI_ID = "poi_0001"


@pytest.fixture(autouse=True)
def clear_contract_records():
    profile_store.clear()
    trip_store.clear()
    yield
    profile_store.clear()
    trip_store.clear()


def _create_trip() -> dict:
    response = client.post(
        "/api/v1/trips",
        json={"user_id": USER_ID, "route_id": ROUTE_ID},
    )
    assert response.status_code == 201
    return response.json()


def test_openapi_declares_response_models_and_error_contracts():
    api_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/")
    ]
    assert all(
        route.response_model is not None or route.status_code == 204
        for route in api_routes
    )

    schema = app.openapi()
    assert schema["info"]["title"] == "QwenPaw Macau AI Travel Assistant API"
    assert schema["info"]["version"] == "1.0.0"
    assert "404" in schema["paths"]["/api/v1/pois/{poi_id}"]["get"]["responses"]
    assert "422" in schema["paths"]["/api/v1/trips"]["post"]["responses"]
    assert "409" in schema["paths"]["/api/v1/trips/{trip_id}/feedback"]["post"][
        "responses"
    ]


def test_poi_and_route_success_contracts():
    poi = client.get(f"/api/v1/pois/{POI_ID}")
    route = client.get(f"/api/v1/routes/{ROUTE_ID}")
    assert poi.status_code == route.status_code == 200
    assert {
        "poi_id",
        "poi_name",
        "address",
        "longitude",
        "latitude",
        "category",
        "source",
        "created_at",
        "updated_at",
    } <= set(poi.json())
    assert {
        "id",
        "name",
        "theme",
        "duration_label",
        "nodes",
        "description",
    } <= set(route.json())
    assert all(node["poi_id"].startswith("poi_0") for node in route.json()["nodes"])


def test_trip_checkin_favorite_and_feedback_contracts():
    created = _create_trip()
    trip_id = created["trip"]["trip_id"]
    stops = created["trip"]["stop_poi_ids"]
    assert set(created) == {"trip", "progress"}
    assert created["progress"]["completion_ratio"] == 0.0

    checkin = client.post(
        f"/api/v1/trips/{trip_id}/checkins",
        json={"poi_id": stops[0]},
    )
    favorite = client.post(f"/api/v1/users/{USER_ID}/favorites/pois/{POI_ID}")
    conflict = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json={"user_id": USER_ID, "rating": 5},
    )
    assert checkin.status_code == 200
    assert checkin.json()["trip"]["checked_in_poi_ids"] == [stops[0]]
    assert favorite.status_code == 201
    assert {"user_id", "poi_id", "poi_name", "longitude", "latitude", "created_at"} <= set(
        favorite.json()
    )
    assert conflict.status_code == 409
    assert isinstance(conflict.json()["detail"], str)

    for poi_id in stops[1:]:
        completed = client.post(
            f"/api/v1/trips/{trip_id}/checkins",
            json={"poi_id": poi_id},
        )
        assert completed.status_code == 200

    feedback = client.post(
        f"/api/v1/trips/{trip_id}/feedback",
        json={"user_id": USER_ID, "rating": 5, "comment": "contract ok"},
    )
    assert feedback.status_code == 201
    assert {
        "feedback_id",
        "trip_id",
        "user_id",
        "rating",
        "created_at",
        "updated_at",
    } <= set(feedback.json())


def test_404_and_422_error_contracts():
    missing = client.get("/api/v1/pois/definitely-missing")
    invalid = client.get(
        "/api/v1/pois/nearby",
        params={"longitude": 113.5, "latitude": 100},
    )
    assert missing.status_code == 404
    assert isinstance(missing.json()["detail"], str)
    assert invalid.status_code == 422
    assert isinstance(invalid.json()["detail"], list)
