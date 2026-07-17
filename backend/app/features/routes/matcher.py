"""规则化路线匹配（无 API key 第一阶段）。

当前职责已经从“纯模板匹配”升级为：
- 模板路线初筛
- 候选 POI 召回
- 约束式排线

仍然不是最终的 Agent 路线微调器。
"""

from app.models.user import Preference
from app.features.pois.repository import canonical_poi_id

from .candidate_selector import build_candidate_pool
from .explain import build_explanation
from .route_constructor import construct_route
from .repository import list_templates
from app.db.data import load_weights

# UI / Preference.themes → 路线模板 theme 字段
_THEME_TO_ROUTE: dict[str, set[str]] = {
    "heritage": {"文化"},
    "architecture": {"建筑"},
    "photo": {"摄影"},
    "food": {"美食"},
    "family": {"亲子"},
    "leisure": {"休闲"},
    "cotai": {"摄影", "休闲"},  # 路氹度假区主题建筑 / 景观线
}

def _diversify_by_theme(
    results: list[tuple[int, list[str], dict]], top_k: int
) -> list[tuple[int, list[str], dict]]:
    """Prefer distinct route themes so a multi-day plan covers different areas."""
    picked: list[tuple[int, list[str], dict]] = []
    seen_themes: set[str] = set()
    for item in results:
        theme = str(item[2].get("route", {}).get("theme") or item[2].get("selected_template") or "")
        if theme and theme in seen_themes:
            continue
        picked.append(item)
        if theme:
            seen_themes.add(theme)
        if len(picked) >= top_k:
            return picked
    for item in results:
        if item in picked:
            continue
        picked.append(item)
        if len(picked) >= top_k:
            break
    return picked


def match_routes(pref: Preference, top_k: int = 3) -> list[dict]:
    """根据偏好返回 top_k 条最匹配的路线结果。

    处理链路：
    1. 模板路线召回
    2. 候选 POI 召回
    3. 约束式排线
    """
    weights = load_weights()
    poi_heat = {
        canonical_poi_id(poi_id): value
        for poi_id, value in weights.get("poi_heat", {}).items()
    }
    results: list[tuple[int, list[str], dict]] = []

    for template in list_templates():
        score = 0
        reasons: list[str] = []

        # 时长匹配
        label = template.get("duration_label", "")
        if pref.duration == "half-day" and "半日" in label:
            score += 3
            reasons.append("时长契合「半日游」")
        elif pref.duration == "full-day" and "一日" in label:
            score += 3
            reasons.append("时长契合「一日游」")
        elif pref.duration == "evening":
            hours = float(template.get("duration_hours") or 0)
            if hours and hours <= 3.5:
                score += 3
                reasons.append("时长契合「夜间/短途」节奏")
            elif "半日" in label:
                score += 2
                reasons.append("半日模板可压缩为夜间漫步")
        elif pref.duration == "multi-day":
            if "一日" in label:
                score += 4
                reasons.append("适合作为多日行程中的完整一天")
            elif "半日" in label:
                score += 2
                reasons.append("适合作为多日行程中的半日分区线")

        # 体力匹配
        if "less-walk" in pref.physical and template.get("physical_level") == "low":
            score += 3
            reasons.append("步行强度低，适合少走路")
        if "no-backtrack" in pref.physical:
            score += 1
            reasons.append("优先选择顺路模板")

        # 兴趣 / 出行类型匹配
        suitable = set(template.get("suitable_for", []))
        hit_interest = suitable & set(pref.interests)
        if hit_interest:
            score += len(hit_interest)
            reasons.append(f"覆盖兴趣：{'、'.join(hit_interest)}")
        hit_travel = suitable & set(pref.travel_type)
        if hit_travel:
            score += len(hit_travel)
            reasons.append(f"适合：{'、'.join(hit_travel)}")

        # 主题匹配（历史城区 / 路氹度假村等）
        wanted_themes: set[str] = set()
        for tag in pref.themes or []:
            wanted_themes |= _THEME_TO_ROUTE.get(tag, set())
        route_theme = str(template.get("theme") or "")
        template_id = str(template.get("id") or "")
        if wanted_themes and route_theme in wanted_themes:
            score += 4
            reasons.append(f"主题契合「{route_theme}」")
        if "cotai" in (pref.themes or []) and "cotai" in template_id:
            score += 6
            reasons.append("契合路氹度假区主题线")

        # 离线调研热度加成（若有权重表）
        hot = sum(poi_heat.get(node["poi_id"], 0) for node in template["nodes"])
        score += int(hot)
        if hot:
            reasons.append("叠加离线热度权重")

        candidate_pois = build_candidate_pool(template)
        route, applied_constraints = construct_route(template, pref, candidate_pois=candidate_pois)
        if applied_constraints:
            reasons.extend(applied_constraints)
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
        top = _diversify_by_theme(results, top_k)
    else:
        top = results[:top_k]

    return [result for _, _, result in top]
