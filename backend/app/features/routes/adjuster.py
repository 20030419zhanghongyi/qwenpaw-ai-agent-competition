"""无 API key 的规则版路线微调器。

当前不是 QwenPaw Agent，但已经支持真实的轻量路线调整：
- 解析少量高频自然语言意图
- 在现有模板路线与约束式排线基础上做节点增删与重排
- 返回未来 Agent 版本会沿用的结构化字段
"""

from __future__ import annotations

from pydantic import BaseModel

from app.db.data import get_poi
from app.models.user import Preference

from .candidate_selector import build_candidate_pool
from .explain import build_explanation
from .repository import get_template
from .route_constructor import construct_route


class RouteAdjustRequest(BaseModel):
    route_id: str
    instruction: str
    preference: Preference


def adjust_route(request: RouteAdjustRequest, preference_override: Preference | None = None) -> dict:
    """根据自然语言指令做路线微调。

    ``preference_override`` 由 P1 路线 agent 路径传入：agent 把自然语言翻成结构化意图后，
    叠加到 ``Preference`` 直接喂给现成排线引擎（跳过下面的规则版关键词解析）。
    排线算法（construct_route / _apply_route_mutations）一行不改。
    """
    template = get_template(request.route_id)
    if template is None:
        raise ValueError(f"Route template not found: {request.route_id}")

    original_pref = request.preference
    if preference_override is not None:
        # agent 路径：偏好已由 route_agent 叠加好，直接用
        adjusted_pref = preference_override
    else:
        # 规则路径：关键词解析
        adjusted_pref = _apply_instruction_to_preference(original_pref, request.instruction)
    original_node_ids = [node["poi_id"] for node in template.get("nodes", [])]

    candidate_pois = build_candidate_pool(template)
    route, applied_constraints = construct_route(template, adjusted_pref, candidate_pois=candidate_pois)
    route, added_nodes, removed_nodes, reordered_nodes, adjust_notes = _apply_route_mutations(
        route=route,
        instruction=request.instruction,
        candidate_pois=candidate_pois,
    )
    added_nodes = _merge_constructor_added_nodes(original_node_ids, route, candidate_pois, added_nodes)
    removed_nodes = _merge_constructor_removed_nodes(original_node_ids, route, removed_nodes)
    applied_constraints.extend(adjust_notes)

    explanation = build_explanation(
        template_id=template["id"],
        reasons=[f"按指令调整：{request.instruction.strip()}"] + adjust_notes,
        applied_constraints=applied_constraints,
        candidate_pois=candidate_pois,
    )

    return {
        "selected_template": template["id"],
        "instruction": request.instruction,
        "preference_before": original_pref.model_dump(),
        "preference_after": adjusted_pref.model_dump(),
        "route": route,
        "candidate_pois": candidate_pois,
        "removed_nodes": removed_nodes,
        "added_nodes": added_nodes,
        "reordered_nodes": reordered_nodes,
        "rationale": explanation["summary"],
        "applied_constraints": applied_constraints,
        "explanation": explanation,
    }


def _apply_instruction_to_preference(pref: Preference, instruction: str) -> Preference:
    updated = pref.model_copy(deep=True)
    text = instruction.strip()

    if any(keyword in text for keyword in ("不想太累", "少走路", "轻松一点", "别太累")):
        if "less-walk" not in updated.physical:
            updated.physical.append("less-walk")

    if any(keyword in text for keyword in ("不要回头路", "别绕路", "顺路一点")):
        if "no-backtrack" not in updated.physical:
            updated.physical.append("no-backtrack")

    if any(keyword in text for keyword in ("拍照", "摄影", "出片")):
        if "photo" not in updated.interests:
            updated.interests.append("photo")

    if any(keyword in text for keyword in ("美食", "吃点东西", "小吃")):
        if "food" not in updated.interests:
            updated.interests.append("food")

    return updated


def _apply_route_mutations(route: dict, instruction: str, candidate_pois: list[dict]) -> tuple[dict, list[dict], list[dict], list[dict], list[str]]:
    text = instruction.strip()
    added_nodes: list[dict] = []
    removed_nodes: list[dict] = []
    reordered_nodes: list[dict] = []
    notes: list[str] = []

    if any(keyword in text for keyword in ("加个拍照点", "多一点拍照", "加一个拍照点", "想拍照")):
        route, added = _add_candidate_node(route, candidate_pois, prefer_photo=True)
        if added:
            added_nodes.extend(added)
            notes.append("已根据拍照偏好实际插入候选节点")

    if any(keyword in text for keyword in ("吃点东西", "加个美食点", "加一个美食点", "想吃点东西")):
        route, added = _add_candidate_node(route, candidate_pois, prefer_food=True)
        if added:
            added_nodes.extend(added)
            notes.append("已根据美食偏好实际插入候选节点")

    if any(keyword in text for keyword in ("不想太累", "少走路", "轻松一点", "别太累")):
        route, removed = _remove_tail_node(route)
        if removed:
            removed_nodes.append(removed)
            notes.append("已移除末端节点以降低步行与停留负担")

    if any(keyword in text for keyword in ("不要回头路", "别绕路", "顺路一点")):
        route, reordered = _reorder_by_district(route)
        if reordered:
            reordered_nodes.extend(reordered)
            notes.append("已按街区连续性重排节点")

    return route, added_nodes, removed_nodes, reordered_nodes, notes


def _suggest_added_nodes(instruction: str, candidate_pois: list[dict], route: dict) -> list[dict]:
    text = instruction.strip()
    current_ids = {node["poi_id"] for node in route.get("nodes", [])}

    if not any(keyword in text for keyword in ("加个拍照点", "多一点拍照", "加一个拍照点", "想拍照")):
        return []

    suggestions: list[dict] = []
    for entry in candidate_pois:
        for candidate in entry.get("candidates", []):
            if candidate["poi_id"] in current_ids:
                continue
            poi = get_poi(candidate["poi_id"])
            if not poi:
                continue
            if "photo" not in poi.get("suitable_for", []) and "摄影" not in poi.get("theme", []):
                continue
            suggestions.append(
                {
                    "poi_id": candidate["poi_id"],
                    "based_on": entry["source_poi_id"],
                    "reasons": candidate["reasons"],
                }
            )
            break
        if suggestions:
            break
    return suggestions


def _add_candidate_node(route: dict, candidate_pois: list[dict], prefer_photo: bool = False, prefer_food: bool = False) -> tuple[dict, list[dict]]:
    suggestions = _suggest_added_nodes(
        "想拍照" if prefer_photo else "想吃点东西",
        candidate_pois,
        route,
    ) if prefer_photo else _suggest_food_nodes(candidate_pois, route)
    if not suggestions:
        return route, []

    selected = suggestions[0]
    current_ids = {node["poi_id"] for node in route.get("nodes", [])}
    if selected["poi_id"] in current_ids:
        return route, []

    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    source_index = next((i for i, node in enumerate(nodes) if node["poi_id"] == selected["based_on"]), len(nodes) - 1)
    insert_at = min(source_index + 1, len(nodes))
    new_node = {
        "poi_id": selected["poi_id"],
        "order": insert_at + 1,
        "suggested_stay_min": 20 if prefer_photo else 30,
        "note": "按自然语言偏好补充的候选节点",
        "replaceable_with": [],
    }
    nodes.insert(insert_at, new_node)
    _renumber(nodes)
    route["nodes"] = nodes
    route["duration_hours"] = round(route.get("duration_hours", 0.0) + (new_node["suggested_stay_min"] / 60.0), 1)
    route["walk_distance_km"] = round(route.get("walk_distance_km", 0.0) + 0.4, 1)
    route["physical_level"] = "medium" if route["walk_distance_km"] > 2.8 else route.get("physical_level", "low")
    return route, [selected]


def _suggest_food_nodes(candidate_pois: list[dict], route: dict) -> list[dict]:
    current_ids = {node["poi_id"] for node in route.get("nodes", [])}
    suggestions: list[dict] = []
    for entry in candidate_pois:
        for candidate in entry.get("candidates", []):
            if candidate["poi_id"] in current_ids:
                continue
            poi = get_poi(candidate["poi_id"])
            if not poi or "food" not in poi.get("suitable_for", []):
                continue
            suggestions.append(
                {
                    "poi_id": candidate["poi_id"],
                    "based_on": entry["source_poi_id"],
                    "reasons": candidate["reasons"],
                }
            )
            break
        if suggestions:
            break
    return suggestions


def _remove_tail_node(route: dict) -> tuple[dict, dict | None]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    if len(nodes) <= 2:
        return route, None

    removed = nodes.pop()
    _renumber(nodes)
    route["nodes"] = nodes
    route["duration_hours"] = max(1.5, round(route.get("duration_hours", 0.0) - (removed.get("suggested_stay_min", 30) / 60.0), 1))
    route["walk_distance_km"] = max(1.0, round(route.get("walk_distance_km", 0.0) - 0.5, 1))
    route["physical_level"] = "low"
    return route, {"poi_id": removed["poi_id"], "reason": "按少走路偏好移除末端节点"}


def _reorder_by_district(route: dict) -> tuple[dict, list[dict]]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    original = [node["poi_id"] for node in nodes]
    nodes.sort(key=lambda node: (_district_rank(node["poi_id"]), node["order"]))
    _renumber(nodes)
    updated = [node["poi_id"] for node in nodes]
    route["nodes"] = nodes
    if original == updated:
        return route, []
    return route, [{"from": original, "to": updated}]


def _district_rank(poi_id: str) -> tuple[str, str]:
    poi = get_poi(poi_id) or {}
    return poi.get("district", ""), poi_id


def _renumber(nodes: list[dict]) -> None:
    for index, node in enumerate(nodes, start=1):
        node["order"] = index


def _merge_constructor_removed_nodes(original_node_ids: list[str], route: dict, removed_nodes: list[dict]) -> list[dict]:
    current_ids = {node["poi_id"] for node in route.get("nodes", [])}
    removed_ids = {item["poi_id"] for item in removed_nodes}
    merged = removed_nodes[:]
    for poi_id in original_node_ids:
        if poi_id not in current_ids and poi_id not in removed_ids:
            merged.append({"poi_id": poi_id, "reason": "按约束式排线移除"})
    return merged


def _merge_constructor_added_nodes(
    original_node_ids: list[str],
    route: dict,
    candidate_pois: list[dict],
    added_nodes: list[dict],
) -> list[dict]:
    current_ids = {node["poi_id"] for node in route.get("nodes", [])}
    original_ids = set(original_node_ids)
    added_ids = {item["poi_id"] for item in added_nodes}
    merged = added_nodes[:]

    candidate_lookup: dict[str, dict] = {}
    for entry in candidate_pois:
        for candidate in entry.get("candidates", []):
            candidate_lookup[candidate["poi_id"]] = {
                "poi_id": candidate["poi_id"],
                "based_on": entry["source_poi_id"],
                "reasons": candidate["reasons"],
            }

    for poi_id in current_ids - original_ids:
        if poi_id not in added_ids:
            merged.append(candidate_lookup.get(poi_id, {"poi_id": poi_id, "reason": "按约束式排线插入"}))
    return merged
