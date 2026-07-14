"""无 API key 的约束式排线。

当前阶段使用可解释的细粒度规则版实现：
- 优先保持模板结构
- 超出约束时优先尝试“替换节点”
- 有余量时可按偏好“插入节点”
- 最后才裁剪尾部节点

目标不是全局最优，而是让路线调整更像真实 itinerary 规划。
"""

from __future__ import annotations

from copy import deepcopy

from app.models.user import Preference

from .poi_metadata import get_poi_metadata


DURATION_LIMITS = {
    "half-day": 4.5,
    "full-day": 8.0,
    "evening": 2.5,
}

WALK_LIMITS = {
    "less-walk": 2.8,
    "normal": 6.0,
}

INSERTABLE_INTERESTS = {
    "photo": {"photo", "architecture"},
    "food": {"food"},
    "culture": {"culture", "history"},
}


def construct_route(route: dict, pref: Preference, candidate_pois: list[dict] | None = None) -> tuple[dict, list[str]]:
    """按约束返回可执行路线结果与 applied_constraints。"""
    planned = deepcopy(route)
    applied_constraints: list[str] = []

    if candidate_pois is not None:
        planned["candidate_pois"] = candidate_pois

    duration_limit = DURATION_LIMITS.get(pref.duration)
    walk_limit = WALK_LIMITS["less-walk"] if "less-walk" in pref.physical else WALK_LIMITS["normal"]

    if candidate_pois:
        planned, inserted = _insert_candidates_for_interests(planned, pref, candidate_pois, duration_limit, walk_limit)
        if inserted:
            applied_constraints.append("在预算允许内按兴趣补充候选节点")

    if duration_limit is not None:
        planned, changed = _fit_duration(planned, duration_limit, candidate_pois or [])
        if changed:
            applied_constraints.append(f"按时长约束调整至 {duration_limit} 小时内")

    if "less-walk" in pref.physical:
        planned, changed = _fit_walk(planned, walk_limit, candidate_pois or [])
        if changed:
            applied_constraints.append(f"按少走路约束调整至约 {walk_limit}km")

    if "no-backtrack" in pref.physical:
        planned, changed = _reorder_for_continuity(planned)
        applied_constraints.append("优先按街区连续性整理顺序，避免明显回头路")
        if changed:
            applied_constraints.append("已按街区连续性重排节点")

    if planned.get("walk_distance_km", 0.0) <= WALK_LIMITS["less-walk"]:
        planned["physical_level"] = "low"
    elif planned.get("walk_distance_km", 0.0) <= 4.5:
        planned["physical_level"] = "medium"
    else:
        planned["physical_level"] = planned.get("physical_level", "medium")

    return planned, _dedupe(applied_constraints)


def _fit_duration(route: dict, duration_limit: float, candidate_pois: list[dict]) -> tuple[dict, bool]:
    changed = False
    while route.get("duration_hours", 0.0) > duration_limit:
        duration_before_replace = route.get("duration_hours", 0.0)
        route, replaced = _replace_last_expensive_node(route, candidate_pois, prefer_shorter=True)
        if replaced:
            changed = True
            # A same-duration replacement does not move the route toward the limit and can
            # otherwise alternate indefinitely between equally expensive candidates.
            if route.get("duration_hours", 0.0) < duration_before_replace:
                continue
        route, trimmed = _trim_tail_node(route)
        if trimmed:
            changed = True
            continue
        break
    if route.get("duration_hours", 0.0) > duration_limit and len(route.get("nodes", [])) <= 2:
        route["duration_hours"] = duration_limit
        changed = True
    return route, changed


def _fit_walk(route: dict, walk_limit: float, candidate_pois: list[dict]) -> tuple[dict, bool]:
    changed = False
    while route.get("walk_distance_km", 0.0) > walk_limit:
        route, replaced = _replace_last_expensive_node(route, candidate_pois, prefer_same_district=True)
        if replaced:
            changed = True
            continue
        route, trimmed = _trim_tail_node(route)
        if trimmed:
            changed = True
            continue
        break
    if route.get("walk_distance_km", 0.0) > walk_limit and len(route.get("nodes", [])) <= 2:
        route["walk_distance_km"] = walk_limit
        changed = True
    return route, changed


def _insert_candidates_for_interests(
    route: dict,
    pref: Preference,
    candidate_pois: list[dict],
    duration_limit: float | None,
    walk_limit: float,
) -> tuple[dict, bool]:
    current_ids = {node["poi_id"] for node in route.get("nodes", [])}
    inserted = False

    for interest in pref.interests:
        expected_tags = INSERTABLE_INTERESTS.get(interest)
        if not expected_tags:
            continue

        for entry in candidate_pois:
            base_index = _find_node_index(route, entry["source_poi_id"])
            if base_index is None:
                continue

            for candidate in entry.get("candidates", []):
                poi_id = candidate["poi_id"]
                if poi_id in current_ids:
                    continue

                poi = get_poi_metadata(poi_id)
                if not poi:
                    continue

                if not expected_tags & set(poi.get("suitable_for", [])):
                    continue

                stay_min = _default_stay_min(poi)
                next_duration = round(route.get("duration_hours", 0.0) + stay_min / 60.0, 1)
                next_walk = round(route.get("walk_distance_km", 0.0) + 0.4, 1)

                if duration_limit is not None and next_duration > duration_limit:
                    continue
                if "less-walk" in pref.physical and next_walk > walk_limit:
                    continue

                nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
                nodes.insert(
                    base_index + 1,
                    {
                        "poi_id": poi_id,
                        "order": base_index + 2,
                        "suggested_stay_min": stay_min,
                        "note": "按兴趣偏好补充的候选节点",
                        "replaceable_with": [],
                    },
                )
                _renumber_nodes_inplace(nodes)
                route["nodes"] = nodes
                route["duration_hours"] = next_duration
                route["walk_distance_km"] = next_walk
                current_ids.add(poi_id)
                inserted = True
                break

            if inserted:
                break

    return route, inserted


def _replace_last_expensive_node(
    route: dict,
    candidate_pois: list[dict],
    *,
    prefer_shorter: bool = False,
    prefer_same_district: bool = False,
) -> tuple[dict, bool]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    if len(nodes) <= 2:
        return route, False

    target = nodes[-1]
    source_poi = get_poi_metadata(target["poi_id"]) or {}
    target_entry = next((entry for entry in candidate_pois if entry["source_poi_id"] == target["poi_id"]), None)
    if not target_entry:
        return route, False

    current_ids = {node["poi_id"] for node in nodes}
    for candidate in target_entry.get("candidates", []):
        poi_id = candidate["poi_id"]
        if poi_id in current_ids:
            continue
        poi = get_poi_metadata(poi_id)
        if not poi:
            continue
        if prefer_same_district and poi.get("district") != source_poi.get("district"):
            continue

        replacement_stay = _default_stay_min(poi)
        old_stay = target.get("suggested_stay_min", 30)
        if prefer_shorter and replacement_stay > old_stay:
            continue

        target["poi_id"] = poi_id
        target["suggested_stay_min"] = min(old_stay, replacement_stay) if prefer_shorter else replacement_stay
        target["note"] = "按约束替换为更紧凑的候选节点"
        target["replaceable_with"] = []
        route["duration_hours"] = max(1.5, round(route.get("duration_hours", 0.0) - max(old_stay - target["suggested_stay_min"], 0) / 60.0, 1))
        route["walk_distance_km"] = max(1.0, round(route.get("walk_distance_km", 0.0) - (0.3 if prefer_same_district else 0.1), 1))
        route["nodes"] = nodes
        return route, True

    return route, False


def _trim_tail_node(route: dict) -> tuple[dict, bool]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    if len(nodes) <= 2:
        return route, False

    removed = nodes.pop()
    _renumber_nodes_inplace(nodes)
    route["nodes"] = nodes
    route["duration_hours"] = max(1.5, round(route.get("duration_hours", 0.0) - (removed.get("suggested_stay_min", 30) / 60.0), 1))
    route["walk_distance_km"] = max(1.0, round(route.get("walk_distance_km", 0.0) - 0.5, 1))
    route["description"] = f"{route.get('description', '')} 已按约束缩短末端节点。".strip()
    return route, True


def _reorder_for_continuity(route: dict) -> tuple[dict, bool]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    original = [node["poi_id"] for node in nodes]
    nodes.sort(key=lambda node: (_district_rank(node["poi_id"]), node["order"]))
    _renumber_nodes_inplace(nodes)
    route["nodes"] = nodes
    updated = [node["poi_id"] for node in nodes]
    return route, original != updated


def _find_node_index(route: dict, poi_id: str) -> int | None:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    for index, node in enumerate(nodes):
        if node["poi_id"] == poi_id:
            return index
    return None


def _default_stay_min(poi: dict) -> int:
    suitable = set(poi.get("suitable_for", []))
    if "food" in suitable:
        return 30
    if "photo" in suitable:
        return 20
    return 25


def _district_rank(poi_id: str) -> tuple[str, str]:
    poi = get_poi_metadata(poi_id) or {}
    return poi.get("district", ""), poi_id


def _renumber_nodes(route: dict) -> dict:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    _renumber_nodes_inplace(nodes)
    route["nodes"] = nodes
    return route


def _renumber_nodes_inplace(nodes: list[dict]) -> None:
    for index, node in enumerate(nodes, start=1):
        node["order"] = index
        if poi := get_poi_metadata(node["poi_id"]):
            node["district"] = poi.get("district")


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
