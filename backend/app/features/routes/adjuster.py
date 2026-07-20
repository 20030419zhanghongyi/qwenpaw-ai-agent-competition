"""无 API key 的规则版路线微调器。

当前不是 QwenPaw Agent，但已经支持真实的轻量路线调整：
- 解析少量高频自然语言意图
- 在现有模板路线与约束式排线基础上做节点增删与重排
- 返回未来 Agent 版本会沿用的结构化字段
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.guardrails.runtime import sanitize_untrusted_text
from app.models.user import Preference

from .candidate_selector import build_candidate_pool
from .explain import build_explanation
from .geo_order import reorder_nodes_geographically, route_is_cotai_heavy
from .poi_metadata import get_poi_metadata, list_poi_metadata
from .repository import get_template
from .route_constructor import annotate_ticketed_attractions, construct_route


class RouteAdjustRequest(BaseModel):
    route_id: str
    instruction: str = Field(min_length=1, max_length=4000)
    preference: Preference

    @field_validator("instruction")
    @classmethod
    def sanitize_instruction(cls, value: str) -> str:
        value = sanitize_untrusted_text(value)
        if not value:
            raise ValueError("instruction must not be blank")
        return value


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
        # agent 路径：偏好已由 route_agent 叠加好；再叠一层具名地标偏好（cotai 等）
        adjusted_pref = _apply_instruction_to_preference(
            preference_override, request.instruction
        )
    else:
        # 规则路径：关键词解析
        adjusted_pref = _apply_instruction_to_preference(
            original_pref, request.instruction
        )
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
    # Named inserts may add ticketed stops after construct_route; re-annotate.
    applied_constraints.extend(annotate_ticketed_attractions(route))

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


# 高频具名地标 → 规范 poi_id（微调「我想去××」用）
_NAMED_LANDMARKS: list[tuple[tuple[str, ...], str]] = [
    (("威尼斯人", "venetian"), "poi_0020"),
    (("巴黎人", "parisian"), "poi_0021"),
    (("伦敦人", "倫敦人", "londoner", "大笨钟", "大本钟"), "poi_0107"),
    (("永利皇宫", "永利"), "poi_0027"),
    (("新濠影汇", "影汇之星", "studio city"), "poi_0110"),
    (("新濠天地", "摩珀斯", "city of dreams"), "poi_0109"),
    (("澳门银河", "银河"), "poi_0112"),
    (("大三巴",), "poi_0001"),
    (("议事亭前地", "议事亭"), "poi_0002"),
    (("妈阁庙",), "poi_0011"),
]


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

    # 点名路氹地标时补上 cotai，便于后续匹配解释
    cotai_poi_ids = {
        "poi_0020",
        "poi_0021",
        "poi_0107",
        "poi_0027",
        "poi_0109",
        "poi_0110",
        "poi_0112",
    }
    if any(poi_id in cotai_poi_ids for poi_id in resolve_named_poi_ids(text)):
        if "cotai" not in (updated.themes or []):
            updated.themes = [*(updated.themes or []), "cotai"]

    return updated


def resolve_named_poi_ids(instruction: str) -> list[str]:
    """从自然语言里解析想去的具名 POI（规则优先，避免只改文案不改节点）。"""
    text = instruction.strip()
    if not text:
        return []
    lower = text.lower()
    found: list[str] = []

    for aliases, poi_id in _NAMED_LANDMARKS:
        hit = False
        for alias in aliases:
            if alias.isascii():
                if alias.lower() in lower:
                    hit = True
                    break
            elif alias in text:
                hit = True
                break
        if hit and poi_id not in found:
            found.append(poi_id)

    if found:
        return found

    # 兜底：用 POI 中文名 / 别名子串匹配（名称至少 2 字）
    for poi in list_poi_metadata():
        poi_id = str(poi.get("id") or "")
        if not poi_id or poi_id in found:
            continue
        for label in (poi.get("name_zh"), poi.get("alias"), poi.get("name_en")):
            label_s = str(label or "").strip()
            if len(label_s) < 2:
                continue
            if label_s in text or (label_s.isascii() and label_s.lower() in lower):
                found.append(poi_id)
                break
        if len(found) >= 3:
            break
    return found


def _apply_route_mutations(route: dict, instruction: str, candidate_pois: list[dict]) -> tuple[dict, list[dict], list[dict], list[dict], list[str]]:
    text = instruction.strip()
    added_nodes: list[dict] = []
    removed_nodes: list[dict] = []
    reordered_nodes: list[dict] = []
    notes: list[str] = []

    # 具名地标优先：如「我想去威尼斯人」
    named_ids = resolve_named_poi_ids(text)
    if named_ids:
        route, named_added, named_notes = _add_named_pois(route, named_ids)
        added_nodes.extend(named_added)
        notes.extend(named_notes)

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

    if any(keyword in text for keyword in ("不要回头路", "别绕路", "顺路一点")) or (
        named_ids and route_is_cotai_heavy(route.get("nodes", []))
    ):
        route, reordered = _reorder_by_district(
            route, start_poi_id=named_ids[0] if named_ids else None
        )
        if reordered:
            reordered_nodes.extend(reordered)
            notes.append("已按坐标顺路重排节点")

    return route, added_nodes, removed_nodes, reordered_nodes, notes


def _add_named_pois(route: dict, poi_ids: list[str]) -> tuple[dict, list[dict], list[str]]:
    """把用户点名的 POI 插入当前路线（保留进/出境口岸锚点）。"""
    added: list[dict] = []
    notes: list[str] = []
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    current_ids = {node["poi_id"] for node in nodes}

    for poi_id in poi_ids:
        meta = get_poi_metadata(poi_id) or {}
        label = str(meta.get("name_zh") or poi_id)
        if poi_id in current_ids:
            notes.append(f"「{label}」已在当前路线中")
            continue

        entry = [n for n in nodes if n.get("anchor") == "entry"]
        exit_nodes = [n for n in nodes if n.get("anchor") == "exit"]
        middle = [n for n in nodes if n.get("anchor") not in {"entry", "exit"}]

        new_node = {
            "poi_id": poi_id,
            "order": 0,
            "suggested_stay_min": 45,
            "note": f"按你的要求加入：{label}",
            "replaceable_with": [],
        }
        middle.append(new_node)
        nodes = [*entry, *middle, *exit_nodes]
        _renumber(nodes)
        current_ids.add(poi_id)
        added.append(
            {
                "poi_id": poi_id,
                "based_on": middle[0]["poi_id"] if middle else poi_id,
                "reasons": [f"用户点名加入「{label}」"],
            }
        )
        notes.append(f"已加入「{label}」")
        route["duration_hours"] = round(float(route.get("duration_hours") or 0) + 0.7, 1)
        route["walk_distance_km"] = round(float(route.get("walk_distance_km") or 0) + 0.5, 1)

    # 插入后按路氹走廊重排：龙环(北)→金光西→中→永利东→影汇南
    # （避免 威尼斯人→龙环→新濠 的北向折返）
    start_id = poi_ids[0] if poi_ids else None
    nodes, geo_changed = reorder_nodes_geographically(nodes, start_poi_id=start_id)
    route["nodes"] = nodes
    if geo_changed:
        notes.append("已按坐标顺路重排，减少路氹回头路")
    return route, added, notes


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
            poi = get_poi_metadata(candidate["poi_id"])
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
            poi = get_poi_metadata(candidate["poi_id"])
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
    if not suggestions and route.get("nodes"):
        based_on = min(route["nodes"], key=lambda node: node["order"])["poi_id"]
        for poi in list_poi_metadata():
            if poi["id"] in current_ids or "food" not in poi.get("suitable_for", []):
                continue
            suggestions.append(
                {
                    "poi_id": poi["id"],
                    "based_on": based_on,
                    "reasons": ["符合美食偏好"],
                }
            )
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


def _reorder_by_district(
    route: dict, *, start_poi_id: str | None = None
) -> tuple[dict, list[dict]]:
    nodes = sorted(route.get("nodes", []), key=lambda item: item["order"])
    original = [node["poi_id"] for node in nodes]
    if route_is_cotai_heavy(nodes) or any(_coords_available(node["poi_id"]) for node in nodes):
        nodes, changed = reorder_nodes_geographically(nodes, start_poi_id=start_poi_id)
        route["nodes"] = nodes
        updated = [node["poi_id"] for node in nodes]
        if not changed:
            return route, []
        return route, [{"from": original, "to": updated}]
    nodes.sort(key=lambda node: (_district_rank(node["poi_id"]), node["order"]))
    _renumber(nodes)
    updated = [node["poi_id"] for node in nodes]
    route["nodes"] = nodes
    if original == updated:
        return route, []
    return route, [{"from": original, "to": updated}]


def _coords_available(poi_id: str) -> bool:
    poi = get_poi_metadata(poi_id) or {}
    raw = poi.get("coordinates")
    return isinstance(raw, dict) and raw.get("lat") is not None and raw.get("lng") is not None


def _district_rank(poi_id: str) -> tuple[str, str]:
    poi = get_poi_metadata(poi_id) or {}
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
