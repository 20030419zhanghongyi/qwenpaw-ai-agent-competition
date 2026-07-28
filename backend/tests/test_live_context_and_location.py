"""Unit coverage for source-attributed route context and GPS proximity rules."""

from datetime import date
from types import SimpleNamespace

import pytest

from app.features.guide.tts import VOICE_BY_LANGUAGE
from app.features.routes import live_context
from app.features.trips import service as trip_service_module
from app.features.trips.models import Trip, TripStatus
from app.features.trips.service import PoiTooFarError, TripService, distance_meters


def test_live_context_parses_official_weather_and_event_signal(monkeypatch):
    responses = {
        live_context.SMG_CURRENT_WEATHER_URL: """
            <weather><temperature>28</temperature><humidity>76</humidity>
            <rainfall>0</rainfall><weather>Cloudy</weather></weather>
        """,
        live_context.MGTO_EVENT_CALENDAR_URL: "Festival programme — July 28 Main Square",
    }
    monkeypatch.setattr(live_context, "_fetch", lambda url: responses[url])
    live_context._cache.clear()

    context = live_context.get_live_route_context(date(2026, 7, 28).isoformat())

    assert context["weather"]["status"] == "ok"
    assert context["weather"]["temperature_c"] == "28"
    assert context["events"]["events"]
    assert context["crowd_signal"] == "event-proxy"
    assert "实时天气" in context["notes"][0]


def test_distance_meters_supports_gps_checkin_thresholds():
    assert distance_meters(22.1987, 113.5439, 22.1987, 113.5439) == 0
    assert distance_meters(22.1987, 113.5439, 22.1992, 113.5439) == pytest.approx(56, abs=3)


def test_gps_checkin_rejects_coordinates_outside_the_allowed_radius(monkeypatch):
    trip = Trip(
        trip_id="trip-1",
        user_id="user-1",
        route_id="route-1",
        status=TripStatus.ACTIVE,
        stop_poi_ids=["poi-1"],
        checked_in_poi_ids=[],
        created_at="2026-07-28T00:00:00Z",
        updated_at="2026-07-28T00:00:00Z",
    )
    repository = SimpleNamespace(get_trip=lambda _: trip)

    class EmptySession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class PoiLookup:
        def __init__(self, _session):
            pass

        def get_by_id(self, _poi_id):
            return SimpleNamespace(latitude=22.1987, longitude=113.5439)

    monkeypatch.setattr(trip_service_module, "SessionLocal", EmptySession)
    monkeypatch.setattr(trip_service_module, "PoiRepository", PoiLookup)

    with pytest.raises(PoiTooFarError, match="move within 120m"):
        TripService(repository).check_in_at_location(
            "trip-1",
            "poi-1",
            longitude=113.5439,
            latitude=22.2087,
            radius_m=120,
        )


def test_traditional_chinese_and_cantonese_have_a_valid_tts_voice():
    assert VOICE_BY_LANGUAGE["zh-TW"] == "Rocky"
    assert VOICE_BY_LANGUAGE["yue"] == "Rocky"
