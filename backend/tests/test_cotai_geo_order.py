"""Geographic Cotai / Taipa node ordering."""

from app.features.routes.adjuster import _add_named_pois, _apply_route_mutations
from app.features.routes.geo_order import reorder_nodes_geographically


def test_cotai_corridor_longhun_before_strip_then_east():
    """龙环 is a north spur — visit before the Strip, not between Venetian and COD."""
    nodes = [
        {"poi_id": "poi_0027", "order": 1, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0109", "order": 2, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0012", "order": 3, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0020", "order": 4, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
    ]
    ordered, changed = reorder_nodes_geographically(nodes, start_poi_id="poi_0020")
    ids = [node["poi_id"] for node in ordered]
    assert changed
    # 龙环 → 威尼斯人 → 新濠 → 永利（优于 威尼斯人→龙环→新濠 的折返）
    assert ids == ["poi_0012", "poi_0020", "poi_0109", "poi_0027"]


def test_europe_and_wynn_clusters_stay_together():
    nodes = [
        {"poi_id": "poi_0231", "order": 1, "suggested_stay_min": 20, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0107", "order": 2, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0027", "order": 3, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0020", "order": 4, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0230", "order": 5, "suggested_stay_min": 20, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0021", "order": 6, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0109", "order": 7, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
    ]
    ordered, changed = reorder_nodes_geographically(nodes)
    ids = [node["poi_id"] for node in ordered]
    assert changed
    assert ids == [
        "poi_0020",
        "poi_0021",
        "poi_0107",
        "poi_0109",
        "poi_0027",
        "poi_0230",
        "poi_0231",
    ]


def test_adding_venetian_reorders_resort_route_geographically():
    route = {
        "duration_hours": 4.0,
        "walk_distance_km": 2.2,
        "nodes": [
            {"poi_id": "poi_0027", "order": 1, "suggested_stay_min": 45, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0012", "order": 2, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0109", "order": 3, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0110", "order": 4, "suggested_stay_min": 35, "note": "", "replaceable_with": []},
        ],
    }
    updated, added, notes = _add_named_pois(route, ["poi_0020"])
    ids = [node["poi_id"] for node in sorted(updated["nodes"], key=lambda n: n["order"])]
    assert added and added[0]["poi_id"] == "poi_0020"
    # 龙环(北) → 威尼斯人 → 新濠 → 永利 → 影汇(南)
    assert ids == ["poi_0012", "poi_0020", "poi_0109", "poi_0027", "poi_0110"]
    assert any("顺路" in note or "坐标" in note for note in notes)


def test_mutation_我想去威尼斯人_is_geographically_sorted():
    route = {
        "duration_hours": 4.0,
        "walk_distance_km": 2.2,
        "nodes": [
            {"poi_id": "poi_0027", "order": 1, "suggested_stay_min": 45, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0230", "order": 2, "suggested_stay_min": 20, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0231", "order": 3, "suggested_stay_min": 20, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0012", "order": 4, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0109", "order": 5, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
            {"poi_id": "poi_0110", "order": 6, "suggested_stay_min": 35, "note": "", "replaceable_with": []},
        ],
    }
    updated, added, _removed, _reordered, notes = _apply_route_mutations(
        route, "我想去威尼斯人", candidate_pois=[]
    )
    ids = [node["poi_id"] for node in sorted(updated["nodes"], key=lambda n: n["order"])]
    assert "poi_0020" in ids and added
    assert ids == [
        "poi_0012",
        "poi_0020",
        "poi_0109",
        "poi_0027",
        "poi_0230",
        "poi_0231",
        "poi_0110",
    ]
    assert any("加入" in note for note in notes)


def test_port_anchors_preserved_around_geo_reorder():
    nodes = [
        {
            "poi_id": "poi_port_taipa",
            "order": 1,
            "anchor": "entry",
            "suggested_stay_min": 10,
            "note": "",
            "replaceable_with": [],
        },
        {"poi_id": "poi_0027", "order": 2, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0020", "order": 3, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {"poi_id": "poi_0109", "order": 4, "suggested_stay_min": 40, "note": "", "replaceable_with": []},
        {
            "poi_id": "poi_port_exit",
            "order": 5,
            "anchor": "exit",
            "suggested_stay_min": 10,
            "note": "",
            "replaceable_with": [],
        },
    ]
    ordered, changed = reorder_nodes_geographically(nodes)
    ids = [node["poi_id"] for node in ordered]
    assert changed
    assert ids[0] == "poi_port_taipa"
    assert ids[-1] == "poi_port_exit"
    assert ids[1:-1] == ["poi_0020", "poi_0109", "poi_0027"]
