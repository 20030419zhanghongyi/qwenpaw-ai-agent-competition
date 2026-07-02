"""基础冒烟测试：验证配置加载、数据可读、核心接口可用。

运行：  pytest -q
"""

from app.features.routes.candidate_selector import build_candidate_pool, select_candidates_for_node
from app.features.routes.route_constructor import construct_route
from app.features.routes.repository import get_template
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_pois_loaded():
    r = client.get("/api/v1/pois")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_routes_loaded():
    r = client.get("/api/v1/routes")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_route_match_returns_result():
    payload = {
        "duration": "half-day",
        "interests": ["photo", "architecture"],
        "travel_type": ["solo"],
        "physical": ["less-walk"],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    matches = r.json()["matches"]
    assert isinstance(matches, list) and len(matches) >= 1


def test_route_match_without_weights_still_returns_explainable_result():
    payload = {
        "duration": "half-day",
        "interests": ["photo", "architecture"],
        "travel_type": ["solo"],
        "physical": ["less-walk"],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    top = r.json()["matches"][0]
    assert top["selected_template"]
    assert "route" in top
    assert "candidate_pois" in top
    assert "applied_constraints" in top
    assert "explanation" in top


def test_half_day_photo_less_walk_returns_low_physical_route():
    payload = {
        "duration": "half-day",
        "interests": ["photo", "architecture"],
        "travel_type": ["solo"],
        "physical": ["less-walk"],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    top = r.json()["matches"][0]
    assert top["route"]["physical_level"] == "low"


def test_candidate_pool_returns_at_least_one_candidate_for_photo_route():
    route = get_template("photo_halfday")
    assert route is not None
    pool = build_candidate_pool(route)
    assert len(pool) >= 1
    assert any(entry["candidates"] for entry in pool)


def test_explicit_replaceable_candidate_is_ranked_first():
    route = get_template("photo_halfday")
    assert route is not None
    target_node = route["nodes"][-1]
    candidates = select_candidates_for_node(target_node, route, limit=3)
    assert len(candidates) >= 1
    assert candidates[0]["poi_id"] == "poi_fatong"


def test_candidate_pool_prefers_same_or_adjacent_districts():
    route = get_template("culture_halfday")
    assert route is not None
    target_node = route["nodes"][0]  # poi_senado
    candidates = select_candidates_for_node(target_node, route, limit=5)
    assert len(candidates) >= 1
    assert all(candidate["district_relation"] in {"same", "adjacent"} for candidate in candidates)


def test_full_day_history_route_respects_duration_budget():
    payload = {
        "duration": "full-day",
        "interests": ["history", "culture"],
        "travel_type": ["friends"],
        "physical": ["no-backtrack"],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    top = r.json()["matches"][0]
    assert top["route"]["duration_hours"] <= 8.0


def test_family_food_less_walk_route_stays_compact():
    payload = {
        "duration": "half-day",
        "interests": ["food", "culture"],
        "travel_type": ["family"],
        "physical": ["less-walk"],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    top = r.json()["matches"][0]
    assert top["route"]["walk_distance_km"] <= 2.8


def test_route_adjust_supports_less_walk_instruction():
    payload = {
        "route_id": "heritage_fullday",
        "instruction": "我不想太累，少走一点路",
        "preference": {
            "duration": "full-day",
            "interests": ["history", "culture"],
            "travel_type": ["friends"],
            "physical": [],
            "language": "zh-CN",
        },
    }
    r = client.post("/api/v1/routes/adjust", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "less-walk" in data["preference_after"]["physical"]
    assert "route" in data
    assert "explanation" in data


def test_route_adjust_supports_photo_point_suggestion():
    payload = {
        "route_id": "culture_halfday",
        "instruction": "帮我加个拍照点",
        "preference": {
            "duration": "half-day",
            "interests": ["culture"],
            "travel_type": ["solo"],
            "physical": [],
            "language": "zh-CN",
        },
    }
    r = client.post("/api/v1/routes/adjust", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "photo" in data["preference_after"]["interests"]
    assert "added_nodes" in data
    assert len(data["added_nodes"]) >= 1
    added_poi_ids = {item["poi_id"] for item in data["added_nodes"]}
    route_poi_ids = {item["poi_id"] for item in data["route"]["nodes"]}
    assert added_poi_ids & route_poi_ids


def test_route_adjust_less_walk_can_remove_tail_node():
    payload = {
        "route_id": "heritage_fullday",
        "instruction": "我不想太累，少走一点路",
        "preference": {
            "duration": "full-day",
            "interests": ["history", "culture"],
            "travel_type": ["friends"],
            "physical": [],
            "language": "zh-CN",
        },
    }
    r = client.post("/api/v1/routes/adjust", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["removed_nodes"]) >= 1
    assert len(data["route"]["nodes"]) < len(get_template("heritage_fullday")["nodes"])


def test_route_adjust_no_backtrack_can_report_reorder():
    payload = {
        "route_id": "heritage_fullday",
        "instruction": "别绕路，顺路一点",
        "preference": {
            "duration": "full-day",
            "interests": ["history", "culture"],
            "travel_type": ["friends"],
            "physical": [],
            "language": "zh-CN",
        },
    }
    r = client.post("/api/v1/routes/adjust", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "no-backtrack" in data["preference_after"]["physical"]
    assert "reordered_nodes" in data


def test_route_adjust_unknown_route_returns_404():
    payload = {
        "route_id": "missing_route",
        "instruction": "我不想太累",
        "preference": {
            "duration": "half-day",
            "interests": ["photo"],
            "travel_type": ["solo"],
            "physical": [],
            "language": "zh-CN",
        },
    }
    r = client.post("/api/v1/routes/adjust", json=payload)
    assert r.status_code == 404


def test_route_constructor_can_insert_interest_candidate_when_budget_allows():
    template = get_template("culture_halfday")
    assert template is not None
    pool = build_candidate_pool(template)

    class Pref:
        duration = "half-day"
        physical = []
        interests = ["photo"]

    route, constraints = construct_route(template, Pref(), candidate_pois=pool)
    assert len(route["nodes"]) >= len(template["nodes"])
    assert "在预算允许内按兴趣补充候选节点" in constraints


def test_route_constructor_prefers_replacement_before_trim_for_walk_limit():
    template = get_template("heritage_fullday")
    assert template is not None
    pool = build_candidate_pool(template)

    class Pref:
        duration = "full-day"
        physical = ["less-walk"]
        interests = ["history"]

    route, constraints = construct_route(template, Pref(), candidate_pois=pool)
    assert route["walk_distance_km"] <= 2.8
    assert any("按少走路约束调整" in item for item in constraints)
