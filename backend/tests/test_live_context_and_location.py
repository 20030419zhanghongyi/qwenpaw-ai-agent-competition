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
    monkeypatch.setattr(live_context, "_fetch", lambda url: responses.get(url))
    live_context._cache.clear()

    context = live_context.get_live_route_context(date(2026, 7, 28).isoformat())

    assert context["weather"]["status"] == "ok"
    assert context["weather"]["temperature_c"] == "28"
    assert context["events"]["events"]
    assert context["crowd_signal"] == "event-proxy"
    assert "实时天气" in context["notes"][0]


def test_event_parser_matches_monthly_concert_date_range(monkeypatch):
    target = date(2026, 8, 29)
    monkeypatch.setattr(
        live_context,
        "_fetch",
        lambda url: "2026 i-dle World Tour Concert 29-30/8 Upcoming"
        if "whatson" in url
        else None,
    )

    events = live_context._events(target)

    assert events["status"] == "ok"
    assert events["events"]
    assert live_context._event_crowd_level(events) == "high"


def test_weather_advice_recommends_umbrella_for_rainy_arrival(monkeypatch):
    monkeypatch.setattr(live_context, "_fetch", lambda _url: None)
    monkeypatch.setattr(
        live_context,
        "_fetch_json",
        lambda _url, _params: {
            "daily": {
                "time": ["2026-07-28", "2026-07-29"],
                "weather_code": [61, 2],
                "temperature_2m_max": [29, 31],
                "temperature_2m_min": [25, 26],
                "precipitation_probability_max": [70, 20],
                "precipitation_sum": [3.5, 0],
                "wind_speed_10m_max": [18, 15],
            }
        },
    )
    live_context._cache.clear()

    advice = live_context.get_weather_advice("2026-07-28", trip_days=2, language="zh-CN")

    assert advice["status"] == "ok"
    assert advice["flags"]["umbrella"] is True
    assert advice["flags"]["sunscreen"] is True
    assert any("带伞" in item for item in advice["advice"])
    assert advice["days"][0]["condition"] == "小雨"


def test_weather_advice_degrades_when_forecast_unavailable(monkeypatch):
    monkeypatch.setattr(live_context, "_fetch", lambda _url: None)
    monkeypatch.setattr(live_context, "_fetch_json", lambda _url, _params: None)
    live_context._cache.clear()

    advice = live_context.get_weather_advice("bad-date", trip_days=1, language="en")

    assert advice["status"] == "unavailable"
    assert advice["days"] == []
    assert advice["flags"]["umbrella"] is False
    assert "temporarily unavailable" in advice["advice"][0]


def test_weather_advice_prefers_official_smg_forecast(monkeypatch):
    official = """
        <SevenDaysForecast>
          <System><SysPubdate>2026-08-25 14:00</SysPubdate></System>
          <Custom>
            <WeatherForecast>
              <ValidFor>2026-08-28</ValidFor>
              <WeatherStatus>18</WeatherStatus>
              <Temperature><Type>1</Type><Value>33</Value></Temperature>
              <Temperature><Type>2</Type><Value>27</Value></Temperature>
              <WeatherDescription>
                Very hot. Cloudy apart from sunny periods. A few thundery showers later.
              </WeatherDescription>
            </WeatherForecast>
            <IssuedTime>2026-08-25 14:00</IssuedTime>
          </Custom>
        </SevenDaysForecast>
    """
    monkeypatch.setattr(
        live_context,
        "_fetch",
        lambda url: official if url == live_context.SMG_7DAY_FORECAST_URLS["en"] else None,
    )
    monkeypatch.setattr(
        live_context,
        "_fetch_json",
        lambda _url, _params: pytest.fail("Open-Meteo should not run when SMG has the date"),
    )
    live_context._cache.clear()

    advice = live_context.get_weather_advice("2026-08-28", trip_days=1, language="en")

    assert advice["status"] == "ok"
    assert advice["days"][0]["temperature_min_c"] == 27
    assert advice["days"][0]["temperature_max_c"] == 33
    assert advice["days"][0]["precipitation_probability_percent"] is None
    assert "thundery showers later" in advice["days"][0]["condition"]
    assert advice["flags"]["umbrella"] is True
    assert advice["flags"]["indoor_backup"] is True
    assert advice["source"]["name"] == "Macao Meteorological and Geophysical Bureau"
    assert advice["source"]["issued_at"] == "2026-08-25 14:00"


def test_crowd_advice_flags_mainland_golden_week(monkeypatch):
    monkeypatch.setattr(
        live_context,
        "_events",
        lambda _target: {"status": "ok", "events": [], "source": {"name": "events"}},
    )
    live_context._cache.clear()

    advice = live_context.get_crowd_advice("2026-10-03", trip_days=1, language="zh-CN")

    assert advice["status"] == "estimated"
    assert advice["level"] == "very_high"
    assert any(factor["kind"] == "mainland_china_holiday" for factor in advice["factors"])
    assert any("十一黄金周" in factor["note"] for factor in advice["factors"])


def test_crowd_advice_flags_official_concert_signal(monkeypatch):
    monkeypatch.setattr(
        live_context,
        "_events",
        lambda _target: {
            "status": "ok",
            "events": ["2026 Macao World Tour Concert at Cotai Arena"],
            "source": {"name": "events"},
        },
    )
    live_context._cache.clear()

    advice = live_context.get_crowd_advice("2026-08-20", trip_days=1, language="zh-CN")

    assert advice["level"] == "high"
    assert any(factor["kind"] == "official_event_calendar" for factor in advice["factors"])


def test_live_travel_advice_returns_realtime_bundle(monkeypatch):
    monkeypatch.setattr(live_context, "_fetch", lambda _url: None)
    monkeypatch.setattr(live_context, "_fetch_json", lambda _url, _params: None)
    monkeypatch.setattr(
        live_context,
        "_events",
        lambda _target: {"status": "ok", "events": [], "source": {"name": "events"}},
    )
    monkeypatch.setattr(
        live_context,
        "get_bus_operations",
        lambda **_kwargs: {"status": "live", "alerts": [], "source": {"name": "DSAT"}},
    )
    live_context._cache.clear()

    advice = live_context.get_live_travel_advice("2026-05-02", trip_days=2, language="en")

    assert advice["weather"]["status"] == "unavailable"
    assert advice["crowd"]["level"] == "very_high"
    assert advice["transport"]["status"] == "live"
    assert "AMap" in advice["transport"]["notes"][0]
    assert advice["opening_hours"]["status"] == "unavailable"


def test_live_travel_advice_does_not_mutate_cached_transport(monkeypatch):
    monkeypatch.setattr(live_context, "_fetch", lambda _url: None)
    monkeypatch.setattr(live_context, "_fetch_json", lambda _url, _params: None)
    monkeypatch.setattr(
        live_context,
        "_events",
        lambda _target: {"status": "ok", "events": [], "source": {"name": "events"}},
    )
    cached_transport = {
        "status": "live",
        "alerts": [],
        "source": {"name": "DSAT", "url": "https://example.test"},
    }
    monkeypatch.setattr(
        live_context,
        "get_bus_operations",
        lambda **_kwargs: cached_transport,
    )
    live_context._cache.clear()

    first = live_context.get_live_travel_advice("2026-08-31", language="zh-CN")
    second = live_context.get_live_travel_advice("2026-08-31", language="zh-CN")

    assert first["transport"]["sources"] == second["transport"]["sources"]
    assert cached_transport["source"]["name"] == "DSAT"


@pytest.mark.parametrize(
    ("language", "transport_text", "opening_text"),
    [
        ("zh-CN", "巴士报站", "景点开放时间"),
        ("zh-TW", "巴士報站", "景點開放時間"),
        ("en", "Bus Reporting", "Opening hours"),
        ("pt", "autocarros", "horários de funcionamento"),
    ],
)
def test_live_travel_advice_localizes_operational_notes(
    monkeypatch,
    language,
    transport_text,
    opening_text,
):
    monkeypatch.setattr(live_context, "_fetch", lambda _url: None)
    monkeypatch.setattr(live_context, "_fetch_json", lambda _url, _params: None)
    monkeypatch.setattr(
        live_context,
        "_events",
        lambda _target: {"status": "ok", "events": [], "source": {"name": "events"}},
    )
    monkeypatch.setattr(
        live_context,
        "get_bus_operations",
        lambda **_kwargs: {"status": "live", "alerts": [], "source": {"name": "DSAT"}},
    )
    live_context._cache.clear()

    advice = live_context.get_live_travel_advice(
        "2026-08-24",
        trip_days=1,
        language=language,
    )

    assert transport_text in advice["transport"]["notes"][0]
    assert opening_text in advice["opening_hours"]["notes"][0]


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
