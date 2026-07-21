"""Theme-first day allocation — split across days or mix when themes exceed days."""

from app.features.routes.matcher import match_routes
from app.features.routes.poi_metadata import get_poi_metadata
from app.features.routes.theme_days import (
    allocate_theme_days,
    select_pois_for_themes,
    should_use_theme_days,
)
from app.models.user import Preference

_PENINSULA = {"大堂区", "风顺堂区", "望德堂区", "花王堂区", "花地玛堂区"}
_COTAI = {"路氹填海区", "嘉模堂区"}


def _middle_nodes(match: dict) -> list[dict]:
    return [
        n
        for n in (match["route"].get("nodes") or [])
        if n.get("anchor") not in {"entry", "exit"}
    ]


def _themes_covered_by_stops(match: dict, themes: list[str]) -> set[str]:
    """Heuristic: which selected themes have at least one supporting stop."""
    covered: set[str] = set()
    for node in _middle_nodes(match):
        poi = get_poi_metadata(node["poi_id"]) or {}
        district = str(poi.get("district") or "")
        tags = set(poi.get("suitable_for") or [])
        if "cotai" in themes and district in _COTAI:
            covered.add("cotai")
        if "heritage" in themes and district in _PENINSULA and (
            "history" in tags or "culture" in tags or "architecture" in tags
        ):
            covered.add("heritage")
        if "food" in themes and "food" in tags:
            covered.add("food")
        if "architecture" in themes and "architecture" in tags:
            covered.add("architecture")
        if "photo" in themes and "photo" in tags:
            covered.add("photo")
        if "leisure" in themes and ("relax" in tags or district in _COTAI | _PENINSULA):
            covered.add("leisure")
        if "family" in themes and "family" in tags:
            covered.add("family")
    return covered


def test_allocate_three_themes_three_days():
    pref = Preference(
        duration="multi-day",
        trip_days=3,
        themes=["cotai", "heritage", "food"],
        interests=["photo"],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    specs = allocate_theme_days(pref)
    assert len(specs) == 3
    bases = [s.base_theme for s in specs]
    assert bases == ["cotai", "heritage", "food"]
    assert all(not s.mix_themes for s in specs)


def test_allocate_one_day_multi_theme_mixes():
    pref = Preference(
        duration="full-day",
        themes=["cotai", "heritage", "food"],
        interests=["photo"],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    specs = allocate_theme_days(pref)
    assert len(specs) == 1
    assert specs[0].theme_key == "mixed"
    assert specs[0].base_theme == "mixed"
    assert set(specs[0].mix_themes) == {"cotai", "heritage", "food"}
    assert "路氹" in specs[0].label
    assert "历史" in specs[0].label
    assert "美食" in specs[0].label


def test_allocate_three_themes_two_days_balanced_mix():
    """3 themes / 2 days → sizes [2, 1]; first day mixes two themes."""
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai", "heritage", "food"],
        interests=[],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    specs = allocate_theme_days(pref)
    assert len(specs) == 2
    sizes = [len(s.mix_themes) if s.mix_themes else 1 for s in specs]
    assert sorted(sizes, reverse=True) == [2, 1]
    assigned: list[str] = []
    for spec in specs:
        if spec.mix_themes:
            assigned.extend(spec.mix_themes)
        else:
            assigned.append(spec.base_theme)
    assert set(assigned) == {"cotai", "heritage", "food"}
    mixed = next(s for s in specs if s.mix_themes)
    assert len(mixed.mix_themes) == 2


def test_allocate_four_themes_two_days_even_split():
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai", "heritage", "food", "architecture"],
        interests=[],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    specs = allocate_theme_days(pref)
    assert len(specs) == 2
    assert all(len(s.mix_themes) == 2 for s in specs)
    assigned = [t for s in specs for t in s.mix_themes]
    assert set(assigned) == {"cotai", "heritage", "food", "architecture"}


def test_select_pois_for_themes_interleaves():
    ids = select_pois_for_themes(["cotai", "heritage", "food"], limit=9)
    assert len(ids) >= 6
    assert ids[0] != ids[1] or ids[1] != ids[2]


def test_match_one_day_multi_theme_covers_all():
    pref = Preference(
        duration="full-day",
        themes=["cotai", "heritage", "food"],
        entry_port="poi_port_hengqin",
        interests=["photo"],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    assert should_use_theme_days(pref)
    matches = match_routes(pref)
    assert len(matches) == 1
    template_id = str(matches[0]["selected_template"])
    assert template_id.startswith("theme_day_mixed")
    assert "cotai" in template_id
    assert "heritage" in template_id
    assert "food" in template_id

    middle = _middle_nodes(matches[0])
    assert len(middle) >= 5
    covered = _themes_covered_by_stops(matches[0], ["cotai", "heritage", "food"])
    assert covered >= {"cotai", "heritage", "food"}, covered

    mix = matches[0]["route"].get("mix_themes") or []
    assert set(mix) == {"cotai", "heritage", "food"}


def test_match_one_day_two_themes_covers_both():
    pref = Preference(
        duration="half-day",
        themes=["heritage", "food"],
        interests=[],
        physical=["normal"],
        travel_type=["solo"],
        language="zh-CN",
    )
    matches = match_routes(pref)
    assert len(matches) == 1
    assert str(matches[0]["selected_template"]).startswith("theme_day_mixed")
    covered = _themes_covered_by_stops(matches[0], ["heritage", "food"])
    assert "heritage" in covered
    assert "food" in covered


def test_match_three_themes_two_days_covers_all():
    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["cotai", "heritage", "food"],
        entry_port="poi_port_hengqin",
        interests=[],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    matches = match_routes(pref)
    assert len(matches) == 2
    assert any("mixed" in str(m["selected_template"]) for m in matches)

    union_covered: set[str] = set()
    for match in matches:
        middle = _middle_nodes(match)
        assert len(middle) >= 5
        union_covered |= _themes_covered_by_stops(
            match, ["cotai", "heritage", "food"]
        )
        day_mix = match["route"].get("mix_themes") or []
        if day_mix:
            day_covered = _themes_covered_by_stops(match, list(day_mix))
            assert day_covered >= set(day_mix), (day_mix, day_covered)

    assert union_covered >= {"cotai", "heritage", "food"}, union_covered


def test_match_multi_theme_multi_day_splits_corridors():
    pref = Preference(
        duration="multi-day",
        trip_days=3,
        themes=["cotai", "heritage", "food"],
        entry_port="poi_port_hengqin",
        interests=["photo"],
        physical=["normal"],
        travel_type=["friends"],
        language="zh-CN",
    )
    assert should_use_theme_days(pref)
    matches = match_routes(pref)
    assert len(matches) == 3
    ids = [m["selected_template"] for m in matches]
    assert all(str(i).startswith("theme_day_") for i in ids)
    assert not any(str(i).startswith("theme_day_mixed") for i in ids)

    assert "theme_day_cotai" in ids[0] or "cotai" in ids[0]
    assert any("heritage" in str(i) for i in ids)
    assert any("food" in str(i) for i in ids)

    def districts(match: dict) -> set[str]:
        out: set[str] = set()
        for node in match["route"].get("nodes") or []:
            if node.get("anchor") in {"entry", "exit"}:
                continue
            poi = get_poi_metadata(node["poi_id"]) or {}
            if poi.get("district"):
                out.add(str(poi["district"]))
        return out

    day_by_theme = {m["selected_template"]: m for m in matches}
    cotai_match = next(m for t, m in day_by_theme.items() if "cotai" in t)
    heritage_match = next(m for t, m in day_by_theme.items() if "heritage" in t)
    food_match = next(m for t, m in day_by_theme.items() if "food" in t)

    cotai_d = districts(cotai_match)
    heritage_d = districts(heritage_match)
    food_d = districts(food_match)
    assert cotai_d & _COTAI
    assert heritage_d & _PENINSULA
    assert len(heritage_d & _PENINSULA) >= len(heritage_d & _COTAI)
    assert food_d & _PENINSULA

    for match in matches:
        middle = _middle_nodes(match)
        assert len(middle) >= 5
        assert float(match["route"].get("duration_hours") or 0) >= 4.0


def test_empty_themes_defaults_to_theme_day_heritage():
    """Preset library is abandoned; sparse prefs still get a POI-pool theme day."""
    pref = Preference(
        duration="half-day",
        themes=[],
        interests=[],
        physical=["normal"],
        travel_type=["solo"],
        language="zh-CN",
    )
    assert should_use_theme_days(pref)
    matches = match_routes(pref, top_k=1)
    assert matches
    assert str(matches[0]["selected_template"]).startswith("theme_day_")


def test_theme_day_match_persists_route_for_trip_lookup():
    """Theme-day ids are constructed in-memory; match must upsert so trips resolve them."""
    from fastapi.testclient import TestClient

    from app.features.routes.repository import get_template
    from app.main import app

    pref = Preference(
        duration="full-day",
        themes=["food", "family"],
        interests=[],
        physical=["normal"],
        travel_type=["family"],
        language="zh-CN",
    )
    matches = match_routes(pref)
    assert len(matches) == 1
    route_id = str(matches[0]["selected_template"])
    assert route_id == "theme_day_mixed_food_family"
    assert matches[0]["route"]["id"] == route_id

    stored = get_template(route_id)
    assert stored is not None
    assert stored["id"] == route_id
    assert len(stored["nodes"]) >= 3

    client = TestClient(app)
    detail = client.get(f"/api/v1/routes/{route_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == route_id

    # Preset catalog must stay free of generated theme-day rows.
    listed = client.get("/api/v1/routes")
    assert listed.status_code == 200
    assert all(not item["id"].startswith("theme_day_") for item in listed.json())

    trip = client.post(
        "/api/v1/trips",
        json={
            "user_id": "theme-day-tripper",
            "route_id": route_id,
            "stop_poi_ids": [n["poi_id"] for n in matches[0]["route"]["nodes"]],
        },
    )
    assert trip.status_code == 201, trip.text
    assert trip.json()["trip"]["route_id"] == route_id
    assert trip.json()["trip"]["status"] == "active"


def test_multi_day_theme_routes_persist_each_day():
    from app.features.routes.repository import get_template

    pref = Preference(
        duration="multi-day",
        trip_days=2,
        themes=["food", "family"],
        interests=[],
        physical=["normal"],
        travel_type=["family"],
        language="zh-CN",
    )
    matches = match_routes(pref)
    assert len(matches) == 2
    for match in matches:
        route_id = str(match["selected_template"])
        assert route_id.startswith("theme_day_")
        stored = get_template(route_id)
        assert stored is not None
        assert stored["id"] == route_id
        assert len(stored["nodes"]) >= 3
