"""无 API key 的候选 POI 召回。

主信号：theme / suitable_for / district / replaceable_with（POI 结构化字段）。
离线 weights.json（热度 / 人流 / 主题偏好）仅作极弱参考，不再主导排序。
联网调研提示由 route_research 提供，不在此模块打分。
"""

from __future__ import annotations

from app.db.data import load_weights
from app.features.pois.repository import canonical_poi_id

from .poi_metadata import get_poi_metadata, list_poi_metadata

ADJACENT_DISTRICTS: dict[str, set[str]] = {
    # 澳门官方 8 堂区（freguesia）。半岛堂区北→南、西→东；离岛堂区经路氹相连。
    # district 值已由 scripts/merge_db.py 统一为官方堂区名。
    "花地玛堂区": {"花王堂区", "望德堂区"},
    "花王堂区": {"花地玛堂区", "望德堂区", "大堂区"},
    "望德堂区": {"花地玛堂区", "花王堂区", "大堂区"},
    "大堂区": {"花王堂区", "望德堂区", "风顺堂区"},
    "风顺堂区": {"大堂区"},
    "嘉模堂区": {"路氹填海区"},
    "路氹填海区": {"嘉模堂区", "圣方济各堂区"},
    "圣方济各堂区": {"路氹填海区"},
}

LOW_BURDEN_TAGS = {"relax", "family", "less-walk"}
CROWD_PAIN_POINTS = {"排队", "人多", "热门时段拥挤"}
BURDEN_PAIN_POINTS = {"暴走", "上坡", "台阶多"}

# Offline XHS weights are kept only as a tiny tie-breaker (max +1 / -1).
_WEIGHT_SIGNAL_CAP = 1


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
    poi = get_poi_metadata(node["poi_id"])
    if not poi:
        return []

    weights = load_weights()
    heat = _canonical_map(weights.get("poi_heat", {}))
    crowd_risk = _canonical_map(weights.get("crowd_risk", {}))
    pain_point_tags = _canonical_map(weights.get("pain_point_tags", {}))
    alt_poi_candidates = {
        canonical_poi_id(source): [canonical_poi_id(item) for item in alternatives]
        for source, alternatives in weights.get("alt_poi_candidates", {}).items()
    }
    theme_bias = {
        theme: _canonical_map(values)
        for theme, values in weights.get("theme_bias", {}).items()
    }
    explicit_replaceable = set(node.get("replaceable_with", []))
    curated_alternatives = set(alt_poi_candidates.get(poi["id"], []))
    all_pois = list_poi_metadata()
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
            score += 1
            reasons.append("离线替代候选（弱参考）")

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

        raw_theme_boost = int(theme_bias.get(route_theme, {}).get(other_id, 0)) if route_theme else 0
        theme_boost = min(raw_theme_boost, _WEIGHT_SIGNAL_CAP) if raw_theme_boost else 0
        if theme_boost:
            score += theme_boost
            reasons.append(f"{route_theme}离线主题偏好（弱）")

        if district_relation == "same":
            score += 4
            reasons.append("同区替换")
        elif district_relation == "adjacent":
            score += 2
            reasons.append("相邻区可串联")
        elif other_id not in explicit_replaceable and not theme_overlap:
            # 非同区、非相邻区、且和源节点主题都不接近时，直接过滤掉。
            continue

        raw_heat = int(heat.get(other_id, 0) or 0)
        heat_score = min(1, raw_heat) if raw_heat > 0 else 0
        if heat_score:
            score += heat_score
            reasons.append("离线热度（弱参考）")

        risk_score = min(int(crowd_risk.get(other_id, 0) or 0), _WEIGHT_SIGNAL_CAP)
        pain_points = pain_point_tags.get(other_id, [])
        penalty = _experience_penalty(route_suitable, risk_score, pain_points)
        if penalty:
            score -= min(penalty, _WEIGHT_SIGNAL_CAP)
            reasons.append("人流/体感风险（弱降权）")

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

    ranked = [
        candidate
        for _, candidate in sorted(
            candidates,
            key=lambda item: (item[1]["explicit_replaceable"], item[0]),
            reverse=True,
        )
    ]
    ranked = _prefer_nearby_candidates(ranked)
    return ranked[:limit]


def build_candidate_pool(route: dict, limit_per_node: int = 3) -> list[dict]:
    """为整条路线构建候选池。"""
    pool: list[dict] = []
    for node in sorted(route.get("nodes", []), key=lambda item: item["order"]):
        pool.append(
            {
                "source_poi_id": node["poi_id"],
                "source_district": (get_poi_metadata(node["poi_id"]) or {}).get(
                    "district"
                ),
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


def _canonical_map(values: dict) -> dict:
    return {canonical_poi_id(poi_id): value for poi_id, value in values.items()}
