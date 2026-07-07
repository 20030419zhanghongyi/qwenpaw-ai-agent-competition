"""无 API key 的候选 POI 召回。

当前阶段依赖本地种子数据与离线权重表 `weights.json`：
- theme
- suitable_for
- district
- replaceable_with
- poi_heat
- crowd_risk / pain_point_tags
- alt_poi_candidates
- theme_bias

目标不是求“语义最相似”，而是给路线微调与解释层提供
更贴近真实路线规划的可替换 / 可补充候选点池：
- 优先和源节点相似
- 优先和整条路线主题一致
- 优先同区或相邻区，减少跨区乱跳
- 显式 replaceable_with 始终有最高优先级
- 用离线调研信号避免把高风险热门点一股脑塞进轻松路线
"""

from __future__ import annotations

from app.db.data import get_poi, load_pois, load_weights

ADJACENT_DISTRICTS: dict[str, set[str]] = {
    "议事亭前地": {"福隆新街", "望德堂区", "风顺堂区"},
    "福隆新街": {"议事亭前地", "下环区", "风顺堂区"},
    "望德堂区": {"议事亭前地", "风顺堂区"},
    "风顺堂区": {"议事亭前地", "福隆新街", "妈阁", "望德堂区"},
    "妈阁": {"风顺堂区", "下环区"},
    "下环区": {"福隆新街", "妈阁"},
    "氹仔旧城区": {"氹仔"},
    "氹仔": {"氹仔旧城区"},
    "路环市区": {"路环市区"},
}

LOW_BURDEN_TAGS = {"relax", "family", "less-walk"}
CROWD_PAIN_POINTS = {"排队", "人多", "热门时段拥挤"}
BURDEN_PAIN_POINTS = {"暴走", "上坡", "台阶多"}


def select_candidates_for_node(
    node: dict,
    route: dict,
    limit: int = 3,
) -> list[dict]:
    """为路线中的一个节点召回候选 POI。

    返回格式：
    [
      {"poi_id": "...", "score": 8, "reasons": ["同主题", "同区替换"]},
      ...
    ]
    """
    poi = get_poi(node["poi_id"])
    if not poi:
        return []

    weights = load_weights()
    heat = weights.get("poi_heat", {})
    crowd_risk = weights.get("crowd_risk", {})
    pain_point_tags = weights.get("pain_point_tags", {})
    alt_poi_candidates = weights.get("alt_poi_candidates", {})
    theme_bias = weights.get("theme_bias", {})
    explicit_replaceable = set(node.get("replaceable_with", []))
    curated_alternatives = set(alt_poi_candidates.get(poi["id"], []))
    all_pois = load_pois()
    candidates: list[tuple[int, dict]] = []
    route_theme = route.get("theme")
    route_suitable = set(route.get("suitable_for", []))
    source_theme = set(poi.get("theme", []))
    source_suitable = set(poi.get("suitable_for", []))

    for other in all_pois:
        other_id = other["id"]
        if other_id == poi["id"]:
            continue

        score = 0
        reasons: list[str] = []

        other_theme = set(other.get("theme", []))
        other_suitable = set(other.get("suitable_for", []))
        district_relation = _district_relation(poi.get("district", ""), other.get("district", ""))

        if other_id in explicit_replaceable:
            score += 8
            reasons.append("模板内可替换点")
        elif other_id in curated_alternatives:
            score += 3
            reasons.append("离线调研替代候选")

        theme_overlap = source_theme & other_theme
        if theme_overlap:
            score += 2 * len(theme_overlap)
            reasons.append(f"同主题：{'、'.join(sorted(theme_overlap))}")

        source_suitable_overlap = source_suitable & other_suitable
        if source_suitable_overlap:
            score += len(source_suitable_overlap)
            reasons.append(f"和源节点场景接近：{'、'.join(sorted(source_suitable_overlap))}")

        suitable_overlap = route_suitable & other_suitable
        if suitable_overlap:
            score += len(suitable_overlap)
            reasons.append(f"适配路线标签：{'、'.join(sorted(suitable_overlap))}")

        if route_theme and route_theme in other.get("theme", []):
            score += 2
            reasons.append("符合路线主主题")

        theme_boost = int(theme_bias.get(route_theme, {}).get(other_id, 0)) if route_theme else 0
        if theme_boost:
            score += theme_boost
            reasons.append(f"{route_theme}主题离线偏好更高")

        if district_relation == "same":
            score += 4
            reasons.append("同区替换")
        elif district_relation == "adjacent":
            score += 2
            reasons.append("相邻区可串联")
        elif other_id not in explicit_replaceable and not theme_overlap:
            # 非同区、非相邻区、且和源节点主题都不接近时，直接过滤掉。
            continue

        heat_score = int(heat.get(other_id, 0))
        if heat_score:
            score += heat_score
            reasons.append("离线热度较高")

        risk_score = int(crowd_risk.get(other_id, 0))
        pain_points = pain_point_tags.get(other_id, [])
        penalty = _experience_penalty(route_suitable, risk_score, pain_points)
        if penalty:
            score -= penalty
            reasons.append("人流或体感风险偏高，已降权")

        # 如果只有“路线大标签”命中，但和源节点本身不相似，适当降权。
        if route_theme and route_theme in other_theme and not theme_overlap and not source_suitable_overlap:
            score -= 1

        if score <= 0:
            continue

        candidates.append(
            (
                score,
                {
                    "poi_id": other_id,
                    "score": score,
                    "reasons": _dedupe(reasons),
                    "district_relation": district_relation,
                    "explicit_replaceable": other_id in explicit_replaceable,
                    "weight_signals": {
                        "poi_heat": heat_score,
                        "crowd_risk": risk_score,
                        "pain_points": pain_points,
                        "theme_bias": theme_boost,
                        "alt_candidate": other_id in curated_alternatives,
                    },
                },
            )
        )

    ranked = [candidate for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True)]
    ranked = _prefer_nearby_candidates(ranked)
    return ranked[:limit]


def build_candidate_pool(route: dict, limit_per_node: int = 3) -> list[dict]:
    """为整条路线构建候选池。"""
    pool: list[dict] = []
    for node in sorted(route.get("nodes", []), key=lambda item: item["order"]):
        pool.append(
            {
                "source_poi_id": node["poi_id"],
                "source_district": (get_poi(node["poi_id"]) or {}).get("district"),
                "candidates": select_candidates_for_node(node, route, limit=limit_per_node),
            }
        )
    return pool


def _district_relation(source: str, target: str) -> str:
    if source == target:
        return "same"
    if target in ADJACENT_DISTRICTS.get(source, set()):
        return "adjacent"
    return "far"


def _prefer_nearby_candidates(candidates: list[dict]) -> list[dict]:
    nearby = [
        candidate for candidate in candidates
        if candidate["district_relation"] in {"same", "adjacent"} or candidate.get("explicit_replaceable")
    ]
    far = [
        candidate for candidate in candidates
        if candidate["district_relation"] == "far" and not candidate.get("explicit_replaceable")
    ]
    return nearby + far


def _experience_penalty(route_suitable: set[str], risk_score: int, pain_points: list[str]) -> int:
    penalty = 0
    pain_point_set = set(pain_points)

    if route_suitable & LOW_BURDEN_TAGS:
        penalty += risk_score
        if pain_point_set & CROWD_PAIN_POINTS:
            penalty += 1
        if pain_point_set & BURDEN_PAIN_POINTS:
            penalty += 1

    return penalty


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
