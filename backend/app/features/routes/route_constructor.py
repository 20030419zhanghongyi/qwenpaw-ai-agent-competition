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

from .geo_order import reorder_nodes_geographically, route_is_cotai_heavy
from .poi_metadata import get_poi_metadata, list_poi_metadata
from .route_research import local_port_transfer_note


DURATION_LIMITS = {
    "half-day": 4.5,
    "full-day": 8.0,
    # Multi-day = one complementary line per day; each day targets a full day.
    "multi-day": 8.0,
    "evening": 2.5,
}

# When multi-day picks a half-day template, expand until a full-day budget.
_MULTI_DAY_MIN_HOURS = 8.0
# Prefer denser stop lists over long dwell padding.
_MULTI_DAY_MIN_STOPS = 8
_MULTI_DAY_FILL_STAY_MIN = 25
_MULTI_DAY_FILL_STAY_MAX = 35
_MULTI_DAY_PAD_STAY_MAX = 50
# Multi-day treats the chosen template as a corridor seed, not a full itinerary.
_MULTI_DAY_SEED_MAX_NODES = 2
_MULTI_DAY_SEED_STAY_CAP_MIN = 40
# Cotai indoor / short hops: don't let synthetic walk km block denser fills.
_MULTI_DAY_FILL_WALK_LIMIT = 9.0
_MULTI_DAY_FILL_WALK_STEP_KM = 0.25

WALK_LIMITS = {
    "less-walk": 2.8,
    "normal": 6.0,
}

INSERTABLE_INTERESTS = {
    "photo": {"photo", "architecture"},
    "food": {"food"},
    "culture": {"culture", "history"},
}

# Ticketed / indoor attractions nested inside a parent venue — not generic corridor fills.
_NESTED_ATTRACTIONS: dict[str, str] = {
    "poi_0114": "poi_0020",  # teamLab @ Venetian mall
}

# Known ticketed Cotai / indoor stops: surface a short paid reminder on the node note.
_TICKETED_ATTRACTION_NOTES: dict[str, str] = {
    "poi_0114": (
        "收费室内展馆（teamLab），须购票入场；票价与开放时间以官方/现场为准，"
        "勿当作免费步行打卡点"
    ),
}

_COTAI_FILL_DISTRICTS = frozenset({"路氹填海区", "嘉模堂区"})


def construct_route(route: dict, pref: Preference, candidate_pois: list[dict] | None = None) -> tuple[dict, list[str]]:
    """按约束返回可执行路线结果与 applied_constraints。"""
    planned = deepcopy(route)
    applied_constraints: list[str] = []

    if candidate_pois is not None:
        planned["candidate_pois"] = candidate_pois

    duration_limit = DURATION_LIMITS.get(pref.duration)
    walk_limit = WALK_LIMITS["less-walk"] if "less-walk" in pref.physical else WALK_LIMITS["normal"]

    # Multi-day: keep a short template seed corridor, then fill toward ~8h.
    if pref.duration == "multi-day":
        planned, seeded = _seed_template_corridor(planned)
        if seeded:
            applied_constraints.append(
                f"多日游以模板前 {_MULTI_DAY_SEED_MAX_NODES} 站为走廊种子，其余由补点生成"
            )

    if candidate_pois:
        planned, inserted = _insert_candidates_for_interests(planned, pref, candidate_pois, duration_limit, walk_limit)
        if inserted:
            applied_constraints.append("在预算允许内按兴趣补充候选节点")

    # Multi-day days should feel like a full day, not a leftover half-day template.
    if pref.duration == "multi-day" and candidate_pois is not None:
        planned, filled = _fill_day_toward_target(
            planned,
            candidate_pois,
            target_hours=_MULTI_DAY_MIN_HOURS,
            ceiling_hours=duration_limit or 8.0,
            walk_limit=walk_limit,
            physical=pref.physical,
        )
        if filled:
            applied_constraints.append(
                f"多日游已将本日扩充至约 {planned.get('duration_hours')} 小时（半日模板补全日）"
            )
            if "半日" in str(planned.get("duration_label") or ""):
                planned["duration_label"] = "一日"
                planned["name"] = f"{planned.get('name', '行程')}（全日扩充）"

    if duration_limit is not None:
        before_nodes = len(planned.get("nodes", []))
        planned, changed = _fit_duration(planned, duration_limit, candidate_pois or [])
        if changed:
            applied_constraints.append(f"按时长约束调整至 {duration_limit} 小时内")
            if len(planned.get("nodes", [])) < before_nodes:
                applied_constraints.append("已按约束缩短末端节点")

    if "less-walk" in pref.physical:
        before_nodes = len(planned.get("nodes", []))
        planned, changed = _fit_walk(planned, walk_limit, candidate_pois or [])
        if changed:
            applied_constraints.append(f"按少走路约束调整至约 {walk_limit}km")
            if len(planned.get("nodes", [])) < before_nodes:
                applied_constraints.append("已按约束缩短末端节点")

    if "no-backtrack" in pref.physical or route_is_cotai_heavy(planned.get("nodes", [])):
        planned, changed = _reorder_for_continuity(planned)
        applied_constraints.append("优先按街区连续性整理顺序，避免明显回头路")
        if changed:
            applied_constraints.append("已按街区连续性重排节点")

    planned, port_notes = _anchor_ports(planned, pref)
    applied_constraints.extend(port_notes)
    transfer_note = _annotate_entry_transfer(planned, pref)
    if transfer_note:
        applied_constraints.append(transfer_note)

    # 口岸锚定后再做一次坐标顺路排（保留 entry/exit），避免路氹点被热度插入打乱。
    if route_is_cotai_heavy(planned.get("nodes", [])):
        nodes, geo_changed = reorder_nodes_geographically(planned.get("nodes", []))
        if geo_changed:
            planned["nodes"] = nodes
            applied_constraints.append("已按坐标重排路氹／氹仔节点，减少回头路")

    if planned.get("walk_distance_km", 0.0) <= WALK_LIMITS["less-walk"]:
        planned["physical_level"] = "low"
    elif planned.get("walk_distance_km", 0.0) <= 4.5:
        planned["physical_level"] = "medium"
    else:
        planned["physical_level"] = planned.get("physical_level", "medium")

    applied_constraints.extend(annotate_ticketed_attractions(planned))
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
                if _should_skip_fill_candidate(poi_id):
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

    target = None
    for candidate_node in reversed(nodes):
        if not _is_port_anchor(candidate_node):
            target = candidate_node
            break
    if target is None:
        return route, False
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

    removable_index = None
    for index in range(len(nodes) - 1, -1, -1):
        if not _is_port_anchor(nodes[index]):
            removable_index = index
            break
    if removable_index is None:
        return route, False
    non_anchors = sum(1 for node in nodes if not _is_port_anchor(node))
    if non_anchors <= 1:
        return route, False

    removed = nodes.pop(removable_index)
    _renumber_nodes_inplace(nodes)
    route["nodes"] = nodes
    route["duration_hours"] = max(1.5, round(route.get("duration_hours", 0.0) - (removed.get("suggested_stay_min", 30) / 60.0), 1))
    route["walk_distance_km"] = max(1.0, round(route.get("walk_distance_km", 0.0) - 0.5, 1))
    # Keep description as the template blurb only. Trim notes belong in applied_constraints
    # (via _fit_duration / _fit_walk), otherwise a multi-trim loop repeats the same suffix.
    return route, True


def _is_port_anchor(node: dict) -> bool:
    return node.get("anchor") in {"entry", "exit"}


def _annotate_entry_transfer(route: dict, pref: Preference) -> str | None:
    """Attach a bus/shuttle tip on the entry port node (not a walking leg)."""
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    entry = next((n for n in nodes if n.get("anchor") == "entry"), None)
    if entry is None:
        return None
    first_stop = next((n for n in nodes if not _is_port_anchor(n)), None)
    tip = local_port_transfer_note(pref.entry_port, first_stop["poi_id"] if first_stop else None)
    if not tip:
        return None
    # Keep the short anchor label; put transfer detail in note for the UI list.
    entry["note"] = tip
    entry["transfer_mode"] = "transit"
    return tip


def annotate_ticketed_attractions(route: dict) -> list[str]:
    """Attach paid-entry reminders on known ticketed nodes (ethics hard rule 10)."""
    notes: list[str] = []
    for node in route.get("nodes", []):
        poi_id = str(node.get("poi_id") or "")
        tip = _TICKETED_ATTRACTION_NOTES.get(poi_id)
        if not tip:
            continue
        existing = str(node.get("note") or "").strip()
        if "购票" in existing or "收费" in existing:
            continue
        node["note"] = f"{existing}；{tip}" if existing else tip
        label = (get_poi_metadata(poi_id) or {}).get("name_zh") or poi_id
        notes.append(f"已提醒「{label}」为收费展馆，须购票")
    return notes


def _should_skip_fill_candidate(poi_id: str) -> bool:
    """Skip nested ticketed stops (e.g. teamLab inside Venetian) as generic fillers."""
    return poi_id in _NESTED_ATTRACTIONS


def _seed_template_corridor(route: dict) -> tuple[dict, bool]:
    """Keep only the first N template stops as a seed; fill/geo corridor builds the rest.

    Lowers how much the full preset node list + long stays dictate a multi-day day.
    """
    nodes = sorted(route.get("nodes") or [], key=lambda item: item.get("order", 0))
    middle = [node for node in nodes if not _is_port_anchor(node)]
    if len(middle) <= _MULTI_DAY_SEED_MAX_NODES:
        # Still soft-cap long template stays so padding/fill owns more of the day.
        capped = False
        for node in middle:
            stay = int(node.get("suggested_stay_min") or 30)
            if stay > _MULTI_DAY_SEED_STAY_CAP_MIN:
                delta_h = (stay - _MULTI_DAY_SEED_STAY_CAP_MIN) / 60.0
                node["suggested_stay_min"] = _MULTI_DAY_SEED_STAY_CAP_MIN
                route["duration_hours"] = max(
                    1.5,
                    round(float(route.get("duration_hours") or 0) - delta_h, 1),
                )
                capped = True
        return route, capped

    kept = middle[:_MULTI_DAY_SEED_MAX_NODES]
    dropped = middle[_MULTI_DAY_SEED_MAX_NODES:]
    removed_hours = 0.0
    for node in dropped:
        removed_hours += float(node.get("suggested_stay_min") or 30) / 60.0
    for node in kept:
        stay = int(node.get("suggested_stay_min") or 30)
        if stay > _MULTI_DAY_SEED_STAY_CAP_MIN:
            removed_hours += (stay - _MULTI_DAY_SEED_STAY_CAP_MIN) / 60.0
            node["suggested_stay_min"] = _MULTI_DAY_SEED_STAY_CAP_MIN
        existing = str(node.get("note") or "").strip()
        if "走廊种子" not in existing:
            node["note"] = f"{existing} · 走廊种子" if existing else "走廊种子"

    _renumber_nodes_inplace(kept)
    route["nodes"] = kept
    route["duration_hours"] = max(
        1.5,
        round(float(route.get("duration_hours") or 0) - removed_hours, 1),
    )
    route["walk_distance_km"] = max(
        0.8,
        round(float(route.get("walk_distance_km") or 0) - 0.4 * len(dropped), 1),
    )
    return route, True


def _is_cotai_corridor_poi(poi_id: str) -> bool:
    poi = get_poi_metadata(poi_id) or {}
    return str(poi.get("district") or "") in _COTAI_FILL_DISTRICTS


def _fill_stay_minutes(poi: dict) -> int:
    """Short dwell for denser multi-day fills (prefer more stops over long stays)."""
    stay = _default_stay_min(poi)
    return max(_MULTI_DAY_FILL_STAY_MIN, min(_MULTI_DAY_FILL_STAY_MAX, stay))


def _middle_stop_count(route: dict) -> int:
    return sum(1 for node in route.get("nodes", []) if not _is_port_anchor(node))


def _needs_more_fill(route: dict, *, target_hours: float) -> bool:
    hours = float(route.get("duration_hours") or 0)
    stops = _middle_stop_count(route)
    return hours < target_hours or stops < _MULTI_DAY_MIN_STOPS


def _cotai_expand_ids(current_ids: set[str]) -> tuple[str, ...]:
    """Curated dense Cotai / Taipa corridor — prioritize landmarks over mall shops."""
    europe = {"poi_0020", "poi_0021", "poi_0107"}
    resort = {"poi_0109", "poi_0027", "poi_0230", "poi_0231", "poi_0110"}
    has_europe = bool(current_ids & europe)
    has_resort = bool(current_ids & resort)
    if has_europe and not has_resort:
        # West strip + 氹仔旧城 denser day; leave deep east strip for day 2.
        return (
            "poi_0012",  # 龙环葡韵
            "poi_0008",  # 官也街
            "poi_0098",  # 嘉模圣母堂
            "poi_0099",  # 嘉模墟
            "poi_0100",  # 北帝庙
            "poi_0137",  # 关帝庙
            "poi_0216",  # 告利雅施利华街
            "poi_0214",  # 施督宪正街
            "poi_0107",  # 伦敦人
            "poi_0106",  # 威尼斯人购物中心（外立面/公共区）
            "poi_0232",  # 大运河购物中心
            "poi_0040",  # 伦敦人综艺馆周边
        )
    if has_resort and not has_europe:
        return (
            "poi_0112",
            "poi_0113",
            "poi_0045",
            "poi_0109",
            "poi_0027",
            "poi_0230",
            "poi_0231",
            "poi_0110",
            "poi_0111",  # 影汇之星
            "poi_0164",
            "poi_0261",
        )
    return (
        "poi_0012",
        "poi_0008",
        "poi_0098",
        "poi_0099",
        "poi_0020",
        "poi_0021",
        "poi_0107",
        "poi_0109",
        "poi_0027",
        "poi_0230",
        "poi_0110",
        "poi_0112",
    )


def _district_fill_ids(current_ids: set[str], *, cotai_heavy: bool) -> list[str]:
    """Extra same-district landmarks when curated list is exhausted."""
    wanted = {"photo", "architecture", "culture", "history", "food", "relax"}
    scored: list[tuple[int, str]] = []
    for poi in list_poi_metadata():
        poi_id = str(poi.get("id") or "")
        if not poi_id or poi_id in current_ids or _should_skip_fill_candidate(poi_id):
            continue
        district = str(poi.get("district") or "")
        if cotai_heavy and district not in _COTAI_FILL_DISTRICTS:
            continue
        if not cotai_heavy and district in _COTAI_FILL_DISTRICTS:
            continue
        tags = set(poi.get("suitable_for") or [])
        if not tags & wanted:
            continue
        # Prefer multi-tag cultural / photo stops over single food shops.
        score = len(tags & wanted) * 2
        if "photo" in tags or "architecture" in tags:
            score += 2
        if "food" in tags and not (tags & {"photo", "architecture", "culture", "history"}):
            score -= 1
        scored.append((score, poi_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [poi_id for _, poi_id in scored[:24]]


def _append_fill_candidates(
    flat: list[tuple[str, dict]],
    *,
    source_fallback: str,
    poi_ids: list[str] | tuple[str, ...],
    current_ids: set[str],
) -> None:
    for poi_id in poi_ids:
        if poi_id in current_ids:
            continue
        flat.append((source_fallback, {"poi_id": poi_id}))


def refill_day_after_dedupe(
    route: dict,
    *,
    blocked_poi_ids: set[str] | None = None,
    physical: list[str] | None = None,
) -> tuple[dict, bool]:
    """Re-densify a day after cross-day POI dedupe removed stops."""
    return _fill_day_toward_target(
        route,
        [],
        target_hours=_MULTI_DAY_MIN_HOURS,
        ceiling_hours=DURATION_LIMITS["multi-day"],
        walk_limit=WALK_LIMITS["normal"],
        physical=physical or ["normal"],
        blocked_poi_ids=blocked_poi_ids,
    )


def _fill_day_toward_target(
    route: dict,
    candidate_pois: list[dict],
    *,
    target_hours: float,
    ceiling_hours: float,
    walk_limit: float,
    physical: list[str],
    blocked_poi_ids: set[str] | None = None,
) -> tuple[dict, bool]:
    """Expand toward a full day by inserting many short stops (pad stays last)."""
    if not _needs_more_fill(route, target_hours=target_hours):
        return route, False

    blocked = set(blocked_poi_ids or ())
    current_ids = {node["poi_id"] for node in route.get("nodes", [])} | blocked
    inserted_any = False
    cotai_heavy = route_is_cotai_heavy(route.get("nodes", []))
    effective_walk_limit = (
        _MULTI_DAY_FILL_WALK_LIMIT if "less-walk" not in physical else walk_limit
    )

    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    last_middle = next(
        (n for n in reversed(nodes) if not _is_port_anchor(n)),
        nodes[-1] if nodes else None,
    )
    source_fallback = last_middle["poi_id"] if last_middle else "poi_0020"

    flat: list[tuple[str, dict]] = []
    if cotai_heavy:
        _append_fill_candidates(
            flat,
            source_fallback=source_fallback,
            poi_ids=_cotai_expand_ids(current_ids),
            current_ids=current_ids,
        )
    else:
        for entry in candidate_pois:
            source = entry.get("source_poi_id")
            if not source:
                continue
            for candidate in entry.get("candidates", []):
                flat.append((source, candidate))

    # Second pass: same-district landmarks so we can hit ~8 stops with short dwells.
    _append_fill_candidates(
        flat,
        source_fallback=source_fallback,
        poi_ids=_district_fill_ids(current_ids, cotai_heavy=cotai_heavy),
        current_ids=current_ids,
    )

    for source_id, candidate in flat:
        if not _needs_more_fill(route, target_hours=target_hours):
            break
        # Once hours are full, still add until min stop count if under ceiling.
        hours = float(route.get("duration_hours") or 0)
        poi_id = candidate.get("poi_id")
        if not poi_id or poi_id in current_ids:
            continue
        if _should_skip_fill_candidate(poi_id):
            continue
        poi = get_poi_metadata(poi_id)
        if not poi:
            continue
        if cotai_heavy and not _is_cotai_corridor_poi(poi_id):
            continue
        base_index = _find_node_index(route, source_id)
        if base_index is None:
            nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
            insert_at = len(nodes)
            for i, node in enumerate(nodes):
                if node.get("anchor") == "exit":
                    insert_at = i
                    break
            base_index = max(insert_at - 1, 0)

        stay_min = _fill_stay_minutes(poi)
        # If hours already meet target, keep adding short stops only while under ceiling
        # and below the min-stop floor (denser itinerary).
        next_duration = round(hours + stay_min / 60.0, 1)
        next_walk = round(
            float(route.get("walk_distance_km") or 0) + _MULTI_DAY_FILL_WALK_STEP_KM,
            1,
        )
        if next_duration > ceiling_hours:
            continue
        if next_walk > effective_walk_limit:
            continue

        nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
        nodes.insert(
            min(base_index + 1, len(nodes)),
            {
                "poi_id": poi_id,
                "order": base_index + 2,
                "suggested_stay_min": stay_min,
                "note": "多日游全日扩充节点",
                "replaceable_with": [],
            },
        )
        _renumber_nodes_inplace(nodes)
        route["nodes"] = nodes
        route["duration_hours"] = next_duration
        route["walk_distance_km"] = next_walk
        current_ids.add(poi_id)
        inserted_any = True

    # Last resort only: small stay pads if still under hours after exhausting POIs.
    if float(route.get("duration_hours") or 0) < target_hours:
        padded = _pad_stays_toward_target(
            route,
            target_hours=target_hours,
            ceiling_hours=ceiling_hours,
        )
        inserted_any = inserted_any or padded

    return route, inserted_any


def _pad_stays_toward_target(
    route: dict,
    *,
    target_hours: float,
    ceiling_hours: float,
) -> bool:
    """Light stay padding only after denser fills are exhausted."""
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    middle = [node for node in nodes if not _is_port_anchor(node)]
    if not middle:
        return False
    changed = False
    guard = 0
    while float(route.get("duration_hours") or 0) < target_hours and guard < 16:
        guard += 1
        progressed = False
        for node in middle:
            current = float(route.get("duration_hours") or 0)
            if current >= target_hours or current >= ceiling_hours:
                break
            stay = int(node.get("suggested_stay_min") or 30)
            if stay >= _MULTI_DAY_PAD_STAY_MAX:
                continue
            room = min(0.15, ceiling_hours - current, target_hours - current)
            if room <= 0:
                break
            node["suggested_stay_min"] = min(_MULTI_DAY_PAD_STAY_MAX, stay + 10)
            route["duration_hours"] = round(current + room, 1)
            changed = True
            progressed = True
        if not progressed:
            break
    route["nodes"] = nodes
    return changed


def _anchor_ports(route: dict, pref: Preference) -> tuple[dict, list[str]]:
    """Prepend entry port and append exit port as fixed anchors."""
    notes: list[str] = []
    nodes = [
        node
        for node in sorted(route.get("nodes", []), key=lambda item: item["order"])
        if not _is_port_anchor(node)
    ]
    entry = (pref.entry_port or "").strip() or None
    exit_port = (pref.exit_port or "").strip() or None

    if entry:
        nodes = [node for node in nodes if node.get("poi_id") != entry]
        nodes.insert(
            0,
            {
                "poi_id": entry,
                "order": 1,
                "suggested_stay_min": 20,
                "note": "进境口岸 · 行程起点",
                "replaceable_with": [],
                "anchor": "entry",
            },
        )
        notes.append("已将进境口岸锚定为行程起点")

    if exit_port:
        nodes = [node for node in nodes if node.get("poi_id") != exit_port]
        nodes.append(
            {
                "poi_id": exit_port,
                "order": len(nodes) + 1,
                "suggested_stay_min": 20,
                "note": "出境口岸 · 行程终点",
                "replaceable_with": [],
                "anchor": "exit",
            },
        )
        notes.append("已将出境口岸锚定为行程终点")

    if notes:
        _renumber_nodes_inplace(nodes)
        route["nodes"] = nodes
        route["duration_hours"] = round(
            float(route.get("duration_hours") or 0) + 0.3 * len(notes),
            1,
        )
    return route, notes


def _reorder_for_continuity(route: dict) -> tuple[dict, bool]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    original = [node["poi_id"] for node in nodes]
    if route_is_cotai_heavy(nodes):
        nodes, changed = reorder_nodes_geographically(nodes)
        route["nodes"] = nodes
        return route, changed
    entry = [node for node in nodes if node.get("anchor") == "entry"]
    exit_nodes = [node for node in nodes if node.get("anchor") == "exit"]
    middle = [node for node in nodes if not _is_port_anchor(node)]
    middle.sort(key=lambda node: (_district_rank(node["poi_id"]), node["order"]))
    nodes = [*entry, *middle, *exit_nodes]
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
