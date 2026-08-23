"""Location-trigger guide API tests (PostGIS-backed)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import Poi
from app.db.session import SessionLocal
from app.features.guide.trigger_state import TriggerState, trigger_state
from app.main import app
from scripts.import_pois import PoiImportRow, upsert_pois

client = TestClient(app)
TEST_POI_ID = "test_guide_trigger_poi"
TEST_COORDINATES = {"longitude": 120.0, "latitude": 20.0}


def _clear_test_poi() -> None:
    with SessionLocal() as session:
        session.execute(delete(Poi).where(Poi.poi_id == TEST_POI_ID))
        session.commit()


@pytest.fixture(autouse=True)
def trigger_test_data():
    _clear_test_poi()
    trigger_state.clear()
    now = datetime.now(timezone.utc)
    upsert_pois(
        [
            PoiImportRow(
                poi_id=TEST_POI_ID,
                poi_name="Trigger Test POI",
                alias=None,
                address="Macau",
                category="test",
                source="pytest",
                created_at=now,
                updated_at=now,
                **TEST_COORDINATES,
            )
        ]
    )
    yield
    trigger_state.clear()
    _clear_test_poi()


def _request(*, session_id: str = "session-a", **extra: object):
    return client.post(
        "/api/v1/guide/trigger",
        json={**TEST_COORDINATES, "session_id": session_id, **extra},
    )


def test_trigger_returns_nearest_poi_prompt_and_guide_request():
    response = _request(language="en")

    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] is True
    assert payload["reason"] is None
    assert payload["poi"]["poi_id"] == TEST_POI_ID
    assert payload["distance_m"] < 0.01
    assert "Trigger Test POI" in payload["prompt"]
    assert payload["guide_request"] == {
        "poi": "Trigger Test POI",
        "language": "en",
        "interests": None,
        "travel_type": None,
        "next_stop": None,
        "next_distance": None,
        "next_walk_time": None,
    }


def test_trigger_returns_no_nearby_poi_without_prompting():
    response = _request(longitude=121.0, latitude=21.0)

    assert response.status_code == 200
    assert response.json() == {
        "triggered": False,
        "reason": "no_nearby_poi",
        "poi": None,
        "distance_m": None,
        "prompt": None,
        "guide_request": None,
    }


def test_trigger_deduplicates_same_session_and_poi():
    assert _request().json()["triggered"] is True

    duplicate = _request()
    assert duplicate.status_code == 200
    assert duplicate.json()["triggered"] is False
    assert duplicate.json()["reason"] == "recently_triggered"
    assert duplicate.json()["poi"]["poi_id"] == TEST_POI_ID


def test_trigger_allows_different_session_for_same_poi():
    assert _request(session_id="session-a").json()["triggered"] is True
    assert _request(session_id="session-b").json()["triggered"] is True


def test_trigger_state_allows_prompt_after_cooldown_expiry():
    state = TriggerState(cooldown=timedelta(minutes=10))
    start = datetime(2026, 7, 16, tzinfo=timezone.utc)

    assert state.allow_prompt(session_id="session", poi_id="poi", now=start) is True
    assert (
        state.allow_prompt(
            session_id="session",
            poi_id="poi",
            now=start + timedelta(minutes=9),
        )
        is False
    )
    assert (
        state.allow_prompt(
            session_id="session",
            poi_id="poi",
            now=start + timedelta(minutes=10),
        )
        is True
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"longitude": 120.0, "latitude": 20.0, "session_id": ""},
        {"longitude": 120.0, "latitude": 20.0, "session_id": "   "},
        {"longitude": 120.0, "latitude": 20.0, "session_id": "valid", "radius_m": 9},
        {"longitude": 120.0, "latitude": 20.0, "session_id": "valid", "radius_m": 501},
        {"longitude": 181.0, "latitude": 20.0, "session_id": "valid"},
        {"longitude": 120.0, "latitude": 91.0, "session_id": "valid"},
    ],
)
def test_trigger_validates_coordinates_radius_and_session_id(payload: dict):
    response = client.post("/api/v1/guide/trigger", json=payload)
    assert response.status_code == 422
