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
from .live_context import get_live_route_context
from .port_events import event_constraint_notes, score_template_for_entry_port
from .route_constructor import construct_route
from .route_research import research_route_tips
from .repository import get_template, list_templates, upsert_constructed_template
from .theme_days import (
    allocate_theme_days,
    build_candidate_pool_for_shell,
    build_theme_day_shell,
    should_use_theme_days,
)
from app.db.data import load_weights


# Fixed story routes have authored chapter order and must only be started explicitly.
NON_RECOMMENDABLE_TEMPLATE_IDS = {"lotus_city_double_map"}
STORY_ROUTE_IDS = {
    "lotus_city_double_map": "lotus_city_double_map",
    "taipa_letters": "taipa_hotspot_halfday",
    "coloane_after_tide": "coloane_leisure_halfday",
}


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


def _finalize_match(
    *,
    route: dict,
    score: int,
    reasons: list[str],
    applied_constraints: list[str],
    selected_template: str,
    candidate_pois: list[dict],
    research_tips: list[str],
    pref: Preference,
    live_context: dict | None = None,
) -> dict:
    event_notes = event_constraint_notes(pref)
    if event_notes:
        applied_constraints = [*applied_constraints, *event_notes]
    if research_tips:
        applied_constraints = [*applied_constraints, *research_tips]
    resolved_live_context = live_context or get_live_route_context(pref.travel_date)
    applied_constraints = [*applied_constraints, *resolved_live_context.get("notes", [])]
    reasons = list(dict.fromkeys([*reasons, *applied_constraints]))
    applied_constraints = list(dict.fromkeys(applied_constraints))
    explanation = build_explanation(
        template_id=selected_template,
        reasons=reasons,
        applied_constraints=applied_constraints,
        candidate_pois=candidate_pois,
    )
    return {
        "route": route,
        "score": score,
        "reasons": reasons,
        "selected_template": selected_template,
        "candidate_pois": candidate_pois,
        "applied_constraints": applied_constraints,
        "explanation": explanation,
        "live_context": resolved_live_context,
    }


def _match_theme_days(pref: Preference, research_tips: list[str], live_context: dict) -> list[dict]:
    """Primary path: one generated day per allocated theme (no preset ranking)."""
    specs = allocate_theme_days(pref)
    matches: list[dict] = []
    for index, spec in enumerate(specs):
        shell = build_theme_day_shell(spec, pref)
        candidate_pois = build_candidate_pool_for_shell(shell)
        route, applied = construct_route(shell, pref, candidate_pois=candidate_pois)
        if spec.mix_themes:
            reasons = [
                f"第 {index + 1} 天混合主题「{spec.label}」从景点池生成",
                "未使用预设模板打分选线",
            ]
        else:
            reasons = [
                f"第 {index + 1} 天按主题「{spec.label}」从景点池生成",
                "未使用预设模板打分选线",
            ]
        matches.append(
            _finalize_match(
                route=route,
                score=100 - index,
                reasons=reasons,
                applied_constraints=applied,
                selected_template=str(shell.get("id") or f"theme_day_{spec.theme_key}"),
                candidate_pois=candidate_pois,
                research_tips=research_tips,
                pref=pref,
                live_context=live_context,
            )
        )
    if pref.duration == "multi-day" and len(matches) > 1:
        matches = _dedupe_multi_day_pois(matches)
    # Persist so POST /trips and GET /routes/{id} can resolve theme_day_* ids.
    for match in matches:
        upsert_constructed_template(match["route"])
    return matches


def _match_preset_templates(
    pref: Preference, top_k: int, research_tips: list[str], live_context: dict
) -> list[dict]:
    """Fallback when themes/interests are empty: legacy template scoring."""
    weights = load_weights()
    poi_heat = {
        canonical_poi_id(poi_id): value
        for poi_id, value in weights.get("poi_heat", {}).items()
    }
    results: list[tuple[int, list[str], dict]] = []
    wants_cotai = "cotai" in (pref.themes or [])

    for template in list_templates():
        if template["id"] in NON_RECOMMENDABLE_TEMPLATE_IDS:
            continue
        score, reasons = score_template_preference(template, pref, poi_heat=poi_heat)
        candidate_pois = build_candidate_pool(template)
        route, applied_constraints = construct_route(
            template, pref, candidate_pois=candidate_pois
        )
        payload = _finalize_match(
            route=route,
            score=score,
            reasons=reasons,
            applied_constraints=applied_constraints,
            selected_template=template["id"],
            candidate_pois=candidate_pois,
            research_tips=research_tips,
            pref=pref,
            live_context=live_context,
        )
        results.append((score, payload["reasons"], payload))

    results.sort(key=lambda x: x[0], reverse=True)
    if pref.duration == "multi-day":
        top = _diversify_by_corridor(results, top_k)
        return _dedupe_multi_day_pois([result for _, _, result in top])
    if wants_cotai:
        top = _prefer_cotai_variants(results, top_k)
    else:
        top = results[:top_k]
    return [result for _, _, result in top]


def _story_match(pref: Preference, research_tips: list[str], live_context: dict) -> dict | None:
    """Build a match from the authored story route without reordering its chapters."""
    route_id = STORY_ROUTE_IDS.get(pref.story_id or "")
    if not route_id:
        return None
    route = get_template(route_id)
    if route is None:
        return None
    candidate_pois = build_candidate_pool(route)
    return _finalize_match(
        route=route,
        score=200,
        reasons=["用户已选择故事体验", "保留故事章节的作者编排顺序"],
        applied_constraints=["故事路线已纳入普通行程；地图、到站、讲解与明信片服务保持可用"],
        selected_template=route_id,
        candidate_pois=candidate_pois,
        research_tips=research_tips,
        pref=pref,
        live_context=live_context,
    )


def _insert_story_day(
    matches: list[dict],
    pref: Preference,
    research_tips: list[str],
    live_context: dict,
) -> list[dict]:
    if pref.story_opt_in is not True or not pref.story_id:
        return matches
    story_match = _story_match(pref, research_tips, live_context)
    if story_match is None:
        return matches
    index = 0
    if pref.duration == "multi-day":
        day_count = clamp_trip_days(pref.trip_days) or TRIP_DAYS_DEFAULT
        index = max(0, min(day_count - 1, (pref.story_day or 1) - 1))
    result = list(matches)
    while len(result) <= index:
        result.append(story_match)
    result[index] = story_match
    return result


def match_routes(pref: Preference, top_k: int | None = None) -> list[dict]:
    """根据偏好返回路线结果。

    主路径：按主题/兴趣从 POI 池生成 theme_day_*（不再依赖预设模板库）。
    预设模板仅在 theme-day 路径异常失败时作为兜底。

    multi-day 时天数取 Preference.trip_days（2–5，缺省 3）。
    """
    resolved_k = resolve_match_top_k(pref) if top_k is None else top_k
    research_tips = research_route_tips(pref)
    live_context = get_live_route_context(pref.travel_date)

    if should_use_theme_days(pref):
        try:
            matches = _match_theme_days(pref, research_tips, live_context)
            return _insert_story_day(matches, pref, research_tips, live_context)
        except Exception:  # noqa: BLE001
            # Fall through to legacy presets only if POI-pool matching blows up.
            pass
    matches = _match_preset_templates(pref, resolved_k, research_tips, live_context)
    return _insert_story_day(matches, pref, research_tips, live_context)
