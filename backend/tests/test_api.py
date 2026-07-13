"""基础冒烟测试：验证配置加载、数据可读、核心接口可用。

运行：  pytest -q
"""

from app.db.data import load_weights
from app.features.routes.candidate_selector import build_candidate_pool, select_candidates_for_node
from app.features.routes.route_constructor import construct_route
from app.features.routes.explain import build_explanation
from app.features.routes.repository import get_template, list_templates
from app.features.routes.poi_metadata import get_poi_metadata
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
    assert candidates[0]["poi_id"] == "poi_0018"


def test_candidate_pool_prefers_same_or_adjacent_districts():
    route = get_template("culture_halfday")
    assert route is not None
    target_node = route["nodes"][0]  # poi_senado
    candidates = select_candidates_for_node(target_node, route, limit=5)
    assert len(candidates) >= 1
    assert all(candidate["district_relation"] in {"same", "adjacent"} for candidate in candidates)


def test_weights_file_contains_expected_sections():
    weights = load_weights()
    assert "poi_heat" in weights
    assert "crowd_risk" in weights
    assert "alt_poi_candidates" in weights
    assert "theme_bias" in weights


def test_curated_alt_candidate_is_marked_in_candidate_signals():
    route = get_template("culture_halfday")
    assert route is not None
    target_node = route["nodes"][0]  # poi_senado
    candidates = select_candidates_for_node(target_node, route, limit=5)
    assert any(
        candidate["weight_signals"]["alt_candidate"]
        and "离线调研替代候选" in candidate["reasons"]
        for candidate in candidates
    )


def test_theme_bias_is_applied_for_matching_route_theme():
    route = get_template("photo_halfday")
    assert route is not None
    target_node = route["nodes"][0]  # poi_paixao
    candidates = select_candidates_for_node(target_node, route, limit=5)
    assert any(candidate["weight_signals"]["theme_bias"] > 0 for candidate in candidates)


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


# ---------------------------------------------------------------------------
# 以下为「无 API key 阶段」补强用例：覆盖此前未测的空白场景，全部纯规则、不依赖外部 API。
# ---------------------------------------------------------------------------


def test_evening_duration_respects_shorter_budget():
    """evening 档（DURATION_LIMITS=2.5h）下，推荐路线应落在晚间预算内。

    设计契约是「尽力裁剪」而非「每条模板都能压进预算」，因此只断言 top match。
    """
    payload = {
        "duration": "evening",
        "interests": ["culture"],
        "travel_type": ["solo"],
        "physical": [],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    top = r.json()["matches"][0]
    assert top["route"]["duration_hours"] <= 2.5


def test_route_adjust_supports_food_point_suggestion():
    """adjust 的美食路径：想吃点东西 → 注入 food 兴趣并实际插入一个美食候选点。"""
    payload = {
        "route_id": "culture_halfday",
        "instruction": "想吃点东西",
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
    assert "food" in data["preference_after"]["interests"]
    assert len(data["added_nodes"]) >= 1

    route_ids = {item["poi_id"] for item in data["route"]["nodes"]}
    added_ids = {item["poi_id"] for item in data["added_nodes"]}
    inserted = added_ids & route_ids
    assert inserted  # 建议的候选点确实落进了最终路线
    # 且至少有一个新增节点是真正的美食 POI
    assert any(
        "food" in (get_poi_metadata(pid) or {}).get("suitable_for", [])
        for pid in inserted
    )


def test_construct_route_no_backtrack_actually_reorders_nodes():
    """no-backtrack 约束应真正按街区连续性重排节点顺序，而不只是附加一条说明文字。"""
    template = get_template("heritage_fullday")
    assert template is not None
    pool = build_candidate_pool(template)

    class Pref:
        duration = "full-day"
        physical = ["no-backtrack"]
        interests = ["history"]

    original_order = [node["poi_id"] for node in sorted(template["nodes"], key=lambda i: i["order"])]
    route, constraints = construct_route(template, Pref(), candidate_pois=pool)
    new_order = [node["poi_id"] for node in sorted(route["nodes"], key=lambda i: i["order"])]
    assert new_order != original_order
    assert any("已按街区连续性重排节点" in item for item in constraints)


def test_match_is_robust_to_unknown_duration_and_empty_preferences():
    """未知 duration + 空 interests/travel_type/physical 不应报错，仍返回有效路线。"""
    payload = {
        "duration": "weekend",
        "interests": [],
        "travel_type": [],
        "physical": [],
        "language": "zh-CN",
    }
    r = client.post("/api/v1/routes/match", json=payload)
    assert r.status_code == 200
    matches = r.json()["matches"]
    assert isinstance(matches, list) and len(matches) >= 1
    assert len(matches[0]["route"]["nodes"]) >= 1


def test_repository_list_and_get_templates():
    """repository 包装层：list_templates 返回全部模板，get_template 命中与未命中。"""
    templates = list_templates()
    assert len(templates) >= 6
    assert all(t.get("id") and t.get("nodes") for t in templates)
    assert get_template("culture_halfday") is not None
    assert get_template("definitely_missing") is None


def test_explain_builds_frontend_friendly_block():
    """explain 层输出结构稳定，且 candidate_overview 每个源节点最多展示 2 个候选、每个候选最多 2 条理由。"""
    candidate_pois = [
        {
            "source_poi_id": "poi_senado",
            "candidates": [
                {"poi_id": f"poi_c{i}", "reasons": ["r1", "r2", "r3"]}
                for i in range(4)
            ],
        }
    ]
    block = build_explanation(
        template_id="culture_halfday",
        reasons=["时长契合「半日游」", "时长契合「半日游」"],
        applied_constraints=["按时长约束调整至 4.5 小时内"],
        candidate_pois=candidate_pois,
    )
    assert block["selected_template"] == "culture_halfday"
    assert block["summary"] == ["时长契合「半日游」"]  # 去重
    assert block["constraints"] == ["按时长约束调整至 4.5 小时内"]
    overview = block["candidate_overview"]
    assert len(overview) == 1
    assert overview[0]["source_poi_id"] == "poi_senado"
    assert len(overview[0]["top_candidates"]) == 2  # 每个源节点封顶 2 个候选
    for candidate in overview[0]["top_candidates"]:
        assert len(candidate["reasons"]) <= 2
