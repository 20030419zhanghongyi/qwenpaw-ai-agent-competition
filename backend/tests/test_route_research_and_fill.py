"""Multi-day full-day fill, port transfer tips, and route research."""

from app.features.routes.matcher import match_routes
from app.features.routes.route_constructor import construct_route
from app.features.routes.route_research import (
    build_research_queries,
    local_port_transfer_note,
    research_route_tips,
)
from app.models.user import Preference


def _cotai_europe_template() -> dict:
    return {
        "id": "cotai_theme_europe_halfday",
        "name": "路氹主题建筑摄影半日线",
        "theme": "摄影",
        "duration_label": "半日",
        "duration_hours": 4.5,
        "walk_distance_km": 1.8,
        "physical_level": "low",
        "nodes": [
            {
                "poi_id": "poi_0020",
                "order": 1,
                "suggested_stay_min": 70,
                "note": "威尼斯人",
                "replaceable_with": ["poi_0114"],
            },
            {
                "poi_id": "poi_0021",
                "order": 2,
                "suggested_stay_min": 50,
                "note": "巴黎人",
                "replaceable_with": [],
            },
            {
                "poi_id": "poi_0107",
                "order": 3,
                "suggested_stay_min": 50,
                "note": "伦敦人",
                "replaceable_with": [],
            },
        ],
    }


def test_local_port_transfer_note_hengqin_to_venetian():
    tip = local_port_transfer_note("poi_port_hengqin", "poi_0020")
    assert tip is not None
    assert "横琴" in tip
    assert "巴士" in tip or "穿梭" in tip
    assert "威尼斯人" in tip


def test_research_tips_include_local_without_web():
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai"],
        entry_port="poi_port_hengqin",
        language="zh-CN",
        interests=["photo"],
        physical=["normal"],
        travel_type=["solo"],
    )
    tips = research_route_tips(pref, enable_web=False)
    assert tips
    assert any("横琴" in tip for tip in tips)
    queries = build_research_queries(pref)
    assert queries
    assert any("横琴" in q or "威尼斯人" in q for q in queries)


def test_multi_day_expands_halfday_cotai_template():
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai"],
        entry_port="poi_port_hengqin",
        language="zh-CN",
        interests=["photo", "architecture"],
        physical=["normal"],
        travel_type=["friends"],
    )
    route, constraints = construct_route(
        _cotai_europe_template(),
        pref,
        candidate_pois=[
            {
                "source_poi_id": "poi_0020",
                "candidates": [{"poi_id": "poi_0012", "score": 5, "reasons": []}],
            }
        ],
    )
    assert float(route["duration_hours"]) >= 7.5
    assert float(route["duration_hours"]) <= 8.5
    assert route.get("duration_label") == "一日" or any("全日" in c for c in constraints)
    nodes = sorted(route["nodes"], key=lambda item: item["order"])
    assert nodes[0]["poi_id"] == "poi_port_hengqin"
    assert nodes[0].get("transfer_mode") == "transit"
    assert "巴士" in (nodes[0].get("note") or "") or "穿梭" in (nodes[0].get("note") or "")
    assert any("扩充" in c or "横琴" in c or "走廊种子" in c for c in constraints)
    # Seed keeps at most 2 template stops; Londoner may be dropped from the preset list.
    middle = [n for n in nodes if n.get("anchor") not in {"entry", "exit"}]
    seed_notes = [n for n in middle if "走廊种子" in str(n.get("note") or "")]
    assert len(seed_notes) <= 2
    # teamLab (replaceable_with on Venetian) must not become a generic fill stop.
    assert "poi_0114" not in {n["poi_id"] for n in nodes}


def test_match_multi_day_cotai_days_are_fuller_and_deduped():
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai"],
        entry_port="poi_port_hengqin",
        language="zh-CN",
        interests=["photo"],
        physical=["normal"],
        travel_type=["friends"],
    )
    matches = match_routes(pref, top_k=2)
    assert len(matches) == 2
    day1_nodes = sorted(matches[0]["route"].get("nodes") or [], key=lambda item: item["order"])
    assert day1_nodes[0]["poi_id"] == "poi_port_hengqin"
    assert day1_nodes[0].get("anchor") == "entry"
    assert "巴士" in (day1_nodes[0].get("note") or "") or "穿梭" in (day1_nodes[0].get("note") or "")
    assert "poi_0114" not in {n["poi_id"] for n in day1_nodes}
    day1_hours = float(matches[0]["route"].get("duration_hours") or 0)
    assert day1_hours >= 7.5
    constraints = " ".join(matches[0].get("applied_constraints") or [])
    assert "横琴" in constraints or "巴士" in constraints or "穿梭" in constraints

    seen: set[str] = set()
    for match in matches:
        hours = float(match["route"].get("duration_hours") or 0)
        assert hours >= 7.5, f"day duration too short: {hours}"
        for node in match["route"].get("nodes") or []:
            if node.get("anchor") in {"entry", "exit"}:
                continue
            poi_id = node["poi_id"]
            assert poi_id not in seen, f"duplicate POI across days: {poi_id}"
            seen.add(poi_id)


def test_construct_route_annotates_teamlab_as_paid():
    pref = Preference(
        duration="half-day",
        language="zh-CN",
        interests=["photo"],
        physical=["normal"],
        travel_type=["solo"],
    )
    template = {
        "id": "teamlab_paid_note",
        "name": "teamLab 提醒",
        "duration_hours": 2.0,
        "walk_distance_km": 0.5,
        "physical_level": "low",
        "nodes": [
            {
                "poi_id": "poi_0114",
                "order": 1,
                "suggested_stay_min": 90,
                "note": "沉浸式光影",
                "replaceable_with": [],
            }
        ],
    }
    route, constraints = construct_route(template, pref, candidate_pois=[])
    node = next(n for n in route["nodes"] if n["poi_id"] == "poi_0114")
    assert "购票" in (node.get("note") or "")
    assert "收费" in (node.get("note") or "")
    assert any("收费" in c or "购票" in c for c in constraints)
