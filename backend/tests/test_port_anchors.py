"""Port anchors + local event crowd notes for route matching."""

from app.features.routes.port_events import event_constraint_notes, score_template_for_entry_port
from app.features.routes.route_constructor import construct_route
from app.models.user import Preference


def _sample_template() -> dict:
    return {
        "id": "heritage_halfday",
        "theme": "文化",
        "duration_hours": 3.5,
        "walk_distance_km": 2.0,
        "nodes": [
            {
                "poi_id": "poi_0001",
                "order": 1,
                "suggested_stay_min": 30,
                "note": "大三巴",
                "replaceable_with": [],
            },
            {
                "poi_id": "poi_0002",
                "order": 2,
                "suggested_stay_min": 25,
                "note": "议事亭",
                "replaceable_with": [],
            },
        ],
    }


def test_construct_route_anchors_entry_and_exit_ports():
    pref = Preference(
        duration="half-day",
        party_size=1,
        travel_type=["solo"],
        interests=["history"],
        physical=["normal"],
        language="zh-CN",
        entry_port="poi_port_guanja",
        exit_port="poi_port_hzmb",
        travel_date="2026-07-20",
    )
    route, constraints = construct_route(_sample_template(), pref)
    nodes = sorted(route["nodes"], key=lambda item: item["order"])
    assert nodes[0]["poi_id"] == "poi_port_guanja"
    assert nodes[0]["anchor"] == "entry"
    assert nodes[-1]["poi_id"] == "poi_port_hzmb"
    assert nodes[-1]["anchor"] == "exit"
    assert any("进境口岸" in note for note in constraints)
    assert any("出境口岸" in note for note in constraints)


def test_match_hengqin_entry_is_first_node_on_cotai_day():
    from app.features.routes.matcher import match_routes

    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai"],
        entry_port="poi_port_hengqin",
        language="zh-CN",
        interests=["photo"],
        physical=["normal"],
        travel_type=["friends"],
        party_size=2,
    )
    matches = match_routes(pref, top_k=1)
    assert matches
    nodes = sorted(matches[0]["route"]["nodes"], key=lambda item: item["order"])
    assert nodes[0]["poi_id"] == "poi_port_hengqin"
    assert nodes[0].get("anchor") == "entry"
    assert nodes[0].get("transfer_mode") == "transit"


def test_event_notes_for_affected_ports_on_travel_date():
    pref = Preference(
        duration="half-day",
        party_size=1,
        travel_type=["solo"],
        interests=[],
        physical=["normal"],
        language="zh-CN",
        entry_port="poi_port_hzmb",
        exit_port="poi_port_hengqin",
        travel_date="2026-07-20",
    )
    notes = event_constraint_notes(pref)
    assert notes
    assert any("估计" in note or "挤" in note for note in notes)


def test_entry_port_region_bias_scores_cotai_templates():
    pref = Preference(
        duration="half-day",
        party_size=1,
        travel_type=["solo"],
        interests=[],
        physical=["normal"],
        language="zh-CN",
        entry_port="poi_port_hengqin",
    )
    score, reasons = score_template_for_entry_port(
        {"id": "cotai_photo", "theme": "摄影"},
        pref,
    )
    assert score > 0
    assert reasons
