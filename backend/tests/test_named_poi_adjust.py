"""Named-landmark route adjustments (e.g. 我想去威尼斯人)."""

from app.features.routes.adjuster import (
    _add_named_pois,
    _apply_route_mutations,
    resolve_named_poi_ids,
)


def test_resolve_venetian_from_natural_language():
    assert resolve_named_poi_ids("我想去威尼斯人") == ["poi_0020"]
    assert resolve_named_poi_ids("加一下巴黎人和伦敦人") == ["poi_0021", "poi_0107"]


def test_add_venetian_into_resort_route():
    route = {
        "id": "cotai_resort_show_halfday",
        "duration_hours": 4.0,
        "walk_distance_km": 2.2,
        "nodes": [
            {
                "poi_id": "poi_0027",
                "order": 1,
                "suggested_stay_min": 45,
                "note": "永利",
                "replaceable_with": [],
            },
            {
                "poi_id": "poi_0109",
                "order": 2,
                "suggested_stay_min": 40,
                "note": "新濠",
                "replaceable_with": [],
            },
        ],
    }
    updated, added, notes = _add_named_pois(route, ["poi_0020"])
    ids = [node["poi_id"] for node in sorted(updated["nodes"], key=lambda n: n["order"])]
    # 威尼斯人(西) → 新濠(中) → 永利(东)
    assert ids == ["poi_0020", "poi_0109", "poi_0027"]
    assert added and added[0]["poi_id"] == "poi_0020"
    assert any("威尼斯人" in note or "加入" in note for note in notes)


def test_mutation_pipeline_inserts_venetian():
    route = {
        "duration_hours": 4.0,
        "walk_distance_km": 2.2,
        "nodes": [
            {
                "poi_id": "poi_0027",
                "order": 1,
                "suggested_stay_min": 45,
                "note": "",
                "replaceable_with": [],
            }
        ],
    }
    updated, added, removed, reordered, notes = _apply_route_mutations(
        route, "我想去威尼斯人", candidate_pois=[]
    )
    assert any(node["poi_id"] == "poi_0020" for node in updated["nodes"])
    assert added
    assert any("加入" in note for note in notes)
    assert not removed
