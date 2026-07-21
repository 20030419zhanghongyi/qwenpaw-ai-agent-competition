"""规则化路线匹配（无 API key 第一阶段）。

当前职责已经从“纯模板匹配”升级为：
- 模板路线初筛
- 候选 POI 召回
- 约束式排线

仍然不是最终的 Agent 路线微调器。
"""

from app.models.user import Preference, TRIP_DAYS_DEFAULT, clamp_trip_days
from app.features.pois.repository import canonical_poi_id

from .candidate_selector import build_candidate_pool
from .explain import build_explanation
from .port_events import event_constraint_notes, score_template_for_entry_port
from .route_constructor import construct_route
from .route_research import research_route_tips
from .repository import list_templates
from app.db.data import load_weights


def resolve_match_top_k(pref: Preference, default: int = 3) -> int:
    """Multi-day plans return one complementary route per day (trip_days)."""
    if pref.duration == "multi-day":
        return clamp_trip_days(pref.trip_days) or TRIP_DAYS_DEFAULT
    return default

# UI / Preference.themes → 路线模板 theme 字段
_THEME_TO_ROUTE: dict[str, set[str]] = {
    "heritage": {"文化"},
    "architecture": {"建筑"},
    "photo": {"摄影"},
    "food": {"美食"},
    "family": {"亲子"},
    "leisure": {"休闲"},
    # 路氹是一整块区域：金光（威尼斯人/巴黎人/伦敦人）与新濠侧同属 Cotai，
    # 选 cotai 时不再靠「摄影 vs 休闲」主题标签拉开两条模板的分差。
    "cotai": set(),
}

# 全部「预设模板固有信号」共用一个预算：时长标签、主题标签、Cotai 区域、
# 模板体力档、离线热度等之和 ≤ 12。兴趣 / 出行类型 / 口岸等偏好外加分不受此帽。
_PRESET_SCORE_CAP = 12

# 显式选路氹时，给所有 cotai_* 模板相同加成（占满预设预算，保证压过半岛热度；
# 金光／新濠同权，再靠兴趣／口岸拉开差距）。
_COTAI_REGION_BONUS = 12

# 离线热度按模板 POI 累加，半岛全日线易到 20+；减半并作为预设子项封顶。
_HEAT_SCORE_CAP = 4


def _is_cotai_template(template_id: str) -> bool:
    return "cotai" in (template_id or "")


def _template_corridor(template_id: str) -> str:
    """Coarse area key for multi-day diversification (not Chinese theme labels)."""
    tid = (template_id or "").lower()
    if "cotai" in tid:
        if "europe" in tid or "theme" in tid:
            return "cotai_west"
        return "cotai_east"
    if "coloane" in tid:
        return "coloane"
    if "taipa" in tid:
        return "taipa"
    return "peninsula"


def _diversify_by_corridor(
    results: list[tuple[int, list[str], dict]], top_k: int
) -> list[tuple[int, list[str], dict]]:
    """Prefer distinct corridors so multi-day plans cover different areas, not theme tags."""
    picked: list[tuple[int, list[str], dict]] = []
    seen: set[str] = set()
    for item in results:
        corridor = _template_corridor(str(item[2].get("selected_template") or ""))
        if corridor in seen:
            continue
        picked.append(item)
        seen.add(corridor)
        if len(picked) >= top_k:
            return picked
    for item in results:
        if item in picked:
            continue
        picked.append(item)
        if len(picked) >= top_k:
            break
    return picked


def _prefer_cotai_variants(
    results: list[tuple[int, list[str], dict]], top_k: int
) -> list[tuple[int, list[str], dict]]:
    """When Cotai is requested, surface 金光 / 新濠 variants before peninsula lines."""
    cotai = [
        item
        for item in results
        if _is_cotai_template(str(item[2].get("selected_template") or ""))
    ]
    other = [item for item in results if item not in cotai]
    return [*cotai, *other][:top_k]


def _dedupe_multi_day_pois(
    matches: list[dict],
) -> list[dict]:
    """Keep first-seen POIs across days so day 2+ don't repeat day 1 stops."""
    from .route_constructor import refill_day_after_dedupe

    seen: set[str] = set()
    for match in matches:
        route = match.get("route") or {}
        nodes = sorted(route.get("nodes") or [], key=lambda item: item.get("order", 0))
        kept: list[dict] = []
        removed_hours = 0.0
        changed = False
        for node in nodes:
            poi_id = str(node.get("poi_id") or "")
            if node.get("anchor") in {"entry", "exit"}:
                kept.append(node)
                continue
            if poi_id and poi_id in seen:
                removed_hours += float(node.get("suggested_stay_min") or 30) / 60.0
                changed = True
                continue
            if poi_id:
                seen.add(poi_id)
            kept.append(node)
        if changed:
            for index, node in enumerate(kept, start=1):
                node["order"] = index
            route["nodes"] = kept
            route["duration_hours"] = max(
                2.0,
                round(float(route.get("duration_hours") or 0) - removed_hours, 1),
            )
            # Day 2+ may become sparse after dedupe — refill with unused short stops.
            blocked = set(seen) - {
                str(n.get("poi_id") or "")
                for n in kept
                if n.get("anchor") not in {"entry", "exit"}
            }
            route, refilled = refill_day_after_dedupe(
                route,
                blocked_poi_ids=blocked,
            )
            match["route"] = route
            for node in route.get("nodes") or []:
                if node.get("anchor") in {"entry", "exit"}:
                    continue
                poi_id = str(node.get("poi_id") or "")
                if poi_id:
                    seen.add(poi_id)
            constraints = list(match.get("applied_constraints") or [])
            constraints.append("多日行程已去掉与前几日重复的景点")
            if refilled:
                constraints.append("去重后已优先补点，避免靠拉长停留凑时长")
            match["applied_constraints"] = list(dict.fromkeys(constraints))
            reasons = list(match.get("reasons") or [])
            reasons.extend(constraints[-2:])
            match["reasons"] = list(dict.fromkeys(reasons))
    return matches


def score_template_preference(
    template: dict,
    pref: Preference,
    *,
    poi_heat: dict[str, float] | None = None,
) -> tuple[int, list[str]]:
    """Score one template against preference (pure function for tests / ranking).

    Formula:
      preset = duration + physical_level + theme + cotai_region + offline_heat
      preset = min(preset, _PRESET_SCORE_CAP)   # ≤ 12
      score  = preset + interests×2 + travel_type + no_backtrack + port
    """
    poi_heat = poi_heat or {}
    preset = 0
    extras = 0
    reasons: list[str] = []
    template_id = str(template.get("id") or "")
    wants_cotai = "cotai" in (pref.themes or [])
    is_cotai = _is_cotai_template(template_id)

    # --- 预设模板固有信号（合计封顶 _PRESET_SCORE_CAP）---

    # 时长匹配（轻量提示；多日不再给「一日模板」过大固定分）
    label = template.get("duration_label", "")
    if pref.duration == "half-day" and "半日" in label:
        preset += 2
        reasons.append("时长契合「半日游」")
    elif pref.duration == "full-day" and "一日" in label:
        preset += 2
        reasons.append("时长契合「一日游」")
    elif pref.duration == "evening":
        hours = float(template.get("duration_hours") or 0)
        if hours and hours <= 3.5:
            preset += 2
            reasons.append("时长契合「夜间/短途」节奏")
        elif "半日" in label:
            preset += 1
            reasons.append("半日模板可压缩为夜间漫步")
    elif pref.duration == "multi-day":
        if "一日" in label:
            preset += 2
            reasons.append("适合作为多日行程中的完整一天")
        elif "半日" in label:
            # Half-day templates are seeded then expanded to ~full day in construct_route.
            preset += 2
            reasons.append("半日模板将扩充为多日游中的完整一天")

    # 模板体力档（与用户少走路偏好对齐时计入预设预算）
    if "less-walk" in pref.physical and template.get("physical_level") == "low":
        preset += 3
        reasons.append("步行强度低，适合少走路")

    # 主题匹配（历史城区等）。cotai 走区域加成，不拆成摄影/休闲分差。
    wanted_themes: set[str] = set()
    for tag in pref.themes or []:
        if tag == "cotai":
            continue
        wanted_themes |= _THEME_TO_ROUTE.get(tag, set())
    route_theme = str(template.get("theme") or "")
    if wanted_themes and route_theme in wanted_themes:
        preset += 2
        reasons.append(f"主题契合「{route_theme}」")

    if wants_cotai:
        if is_cotai:
            # 金光大道线与新濠侧线同属 Cotai，给相同区域分，不用热度拉开差距。
            preset += _COTAI_REGION_BONUS
            reasons.append("契合路氹（Cotai）度假区 · 金光／新濠同权")
        else:
            reasons.append("已选路氹主题，半岛线降权")
        # 显式 Cotai 时不叠加离线热度，避免半岛一日线因热度压过路氹半日线。
    else:
        hot = sum(poi_heat.get(node["poi_id"], 0) for node in template.get("nodes", []))
        heat_score = min(int(hot // 2), _HEAT_SCORE_CAP)
        preset += heat_score
        if heat_score:
            reasons.append("叠加离线热度权重（已弱化）")

    if preset > _PRESET_SCORE_CAP:
        reasons.append(f"预设路线权重已压缩至 {_PRESET_SCORE_CAP}")
    preset = min(preset, _PRESET_SCORE_CAP)

    # --- 偏好外加分（不受预设帽约束，相对决定同区排序）---

    if "no-backtrack" in pref.physical:
        extras += 1
        reasons.append("优先选择顺路模板")

    suitable = set(template.get("suitable_for", []))
    hit_interest = suitable & set(pref.interests)
    if hit_interest:
        extras += len(hit_interest) * 2
        reasons.append(f"覆盖兴趣：{'、'.join(hit_interest)}")
    hit_travel = suitable & set(pref.travel_type)
    if hit_travel:
        extras += len(hit_travel)
        reasons.append(f"适合：{'、'.join(hit_travel)}")

    # 口岸偏置：Cotai 模板在 port_events 内对称加分。
    port_score, port_reasons = score_template_for_entry_port(template, pref)
    extras += port_score
    reasons.extend(port_reasons)

    return preset + extras, reasons


def match_routes(pref: Preference, top_k: int | None = None) -> list[dict]:
    """根据偏好返回 top_k 条最匹配的路线结果。

    处理链路：
    1. 模板路线召回
    2. 候选 POI 召回
    3. 约束式排线

    multi-day 时 top_k 默认取 Preference.trip_days（2–5，缺省 3）。
    """
    resolved_k = resolve_match_top_k(pref) if top_k is None else top_k
    weights = load_weights()
    poi_heat = {
        canonical_poi_id(poi_id): value
        for poi_id, value in weights.get("poi_heat", {}).items()
    }
    results: list[tuple[int, list[str], dict]] = []
    wants_cotai = "cotai" in (pref.themes or [])
    # One web/research pass per match request (not per template) — fail-soft.
    research_tips = research_route_tips(pref)

    for template in list_templates():
        score, reasons = score_template_preference(template, pref, poi_heat=poi_heat)

        candidate_pois = build_candidate_pool(template)
        route, applied_constraints = construct_route(
            template, pref, candidate_pois=candidate_pois
        )
        event_notes = event_constraint_notes(pref)
        if event_notes:
            applied_constraints = [*applied_constraints, *event_notes]
        if research_tips:
            applied_constraints = [*applied_constraints, *research_tips]
        if applied_constraints:
            reasons.extend(applied_constraints)
        # Dedupe reasons while preserving order
        reasons = list(dict.fromkeys(reasons))
        applied_constraints = list(dict.fromkeys(applied_constraints))
        explanation = build_explanation(
            template_id=template["id"],
            reasons=reasons,
            applied_constraints=applied_constraints,
            candidate_pois=candidate_pois,
        )

        results.append(
            (
                score,
                reasons,
                {
                    "route": route,
                    "score": score,
                    "reasons": reasons,
                    "selected_template": template["id"],
                    "candidate_pois": candidate_pois,
                    "applied_constraints": applied_constraints,
                    "explanation": explanation,
                },
            )
        )

    results.sort(key=lambda x: x[0], reverse=True)
    if pref.duration == "multi-day":
        top = _diversify_by_corridor(results, resolved_k)
        return _dedupe_multi_day_pois([result for _, _, result in top])
    if wants_cotai:
        top = _prefer_cotai_variants(results, resolved_k)
    else:
        top = results[:resolved_k]

    return [result for _, _, result in top]
