"""Preference.trip_days clamps and drives multi-day match top_k."""

from fastapi.testclient import TestClient

from app.features.intent.api import parse_intent_rules
from app.features.routes import matcher
from app.features.routes.matcher import match_routes, resolve_match_top_k
from app.main import app
from app.models.user import Preference, TRIP_DAYS_DEFAULT, clamp_trip_days

client = TestClient(app)


def test_clamp_trip_days_bounds():
    assert clamp_trip_days(None) is None
    assert clamp_trip_days(1) == 2
    assert clamp_trip_days(2) == 2
    assert clamp_trip_days(5) == 5
    assert clamp_trip_days(9) == 5


def test_preference_trip_days_validator():
    assert Preference(trip_days=4).trip_days == 4
    assert Preference(trip_days=1).trip_days == 2
    assert Preference(trip_days=99).trip_days == 5
    assert Preference(trip_days="3").trip_days == 3
    assert Preference(trip_days="nope").trip_days is None


def test_resolve_match_top_k_uses_trip_days_for_multi_day():
    assert resolve_match_top_k(Preference(duration="half-day")) == 3
    assert resolve_match_top_k(Preference(duration="multi-day")) == TRIP_DAYS_DEFAULT
    assert resolve_match_top_k(Preference(duration="multi-day", trip_days=2)) == 2
    assert resolve_match_top_k(Preference(duration="multi-day", trip_days=4)) == 4


def test_match_routes_multi_day_respects_trip_days():
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        interests=["history"],
        travel_type=["solo"],
        physical=["normal"],
        language="zh-CN",
    )
    matches = match_routes(pref)
    assert len(matches) == 2

    pref5 = Preference(
        duration="multi-day",
        trip_days=5,
        interests=["history"],
        travel_type=["solo"],
        physical=["normal"],
        language="zh-CN",
    )
    assert len(match_routes(pref5)) == 5


def test_selected_story_replaces_requested_day_with_authored_route():
    pref = Preference(
        duration="multi-day",
        trip_days=3,
        interests=["history"],
        travel_type=["solo"],
        physical=["normal"],
        story_opt_in=True,
        story_id="taipa_letters",
        story_day=2,
    )

    matches = match_routes(pref)

    assert len(matches) == 3
    assert matches[1]["selected_template"] == "taipa_hotspot_halfday"
    assert matches[0]["selected_template"] != "taipa_hotspot_halfday"
    assert matches[2]["selected_template"] != "taipa_hotspot_halfday"


def test_story_preference_fields_are_validated_and_parsed():
    pref = parse_intent_rules("我愿意参加海风寄来的信，安排在第2天")
    assert pref.story_opt_in is True
    assert pref.story_id == "taipa_letters"
    assert pref.story_day == 2

    declined = parse_intent_rules("这次不参加故事")
    assert declined.story_opt_in is False


def test_multiple_story_selections_replace_their_scheduled_days(monkeypatch):
    pref = Preference(
        duration="multi-day",
        trip_days=3,
        story_selections=[
            {"story_id": "taipa_letters", "story_day": 1},
            {"story_id": "coloane_after_tide", "story_day": 3},
        ],
    )
    monkeypatch.setattr(
        matcher,
        "_story_match",
        lambda _pref, _tips, _context, story_id=None: {"selected_template": story_id},
    )

    matches = matcher._insert_story_day(
        [{"selected_template": "day-1"}, {"selected_template": "day-2"}, {"selected_template": "day-3"}],
        pref,
        [],
        {},
    )

    assert [match["selected_template"] for match in matches] == [
        "taipa_letters",
        "day-2",
        "coloane_after_tide",
    ]


def test_match_api_echoes_trip_days():
    """POST /routes/match must accept trip_days and return that many multi-day matches."""
    response = client.post(
        "/api/v1/routes/match",
        json={
            "duration": "multi-day",
            "party_size": 1,
            "travel_type": ["solo"],
            "interests": ["history"],
            "themes": [],
            "physical": ["normal"],
            "language": "zh-CN",
            "trip_days": 4,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["preference"]["trip_days"] == 4
    assert len(body["matches"]) == 4


def test_parse_intent_rules_infers_trip_days():
    pref = parse_intent_rules("想玩三天，多看看历史")
    assert pref.duration == "multi-day"
    assert pref.trip_days == 3
    assert "history" in pref.interests

    pref2 = parse_intent_rules("a 4-day multi-day trip")
    assert pref2.duration == "multi-day"
    assert pref2.trip_days == 4
