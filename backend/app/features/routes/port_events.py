"""Port anchors + local event crowd estimates for route matching."""

from __future__ import annotations

from datetime import date

from app.db.data import get_port, load_events, load_ports
from app.models.user import Preference

# region_bias → score hints for template themes / ids
_REGION_THEME_BONUS: dict[str, tuple[set[str], int]] = {
    "peninsula_north": ({"文化", "建筑", "摄影"}, 3),
    "peninsula_east": ({"文化", "建筑", "美食"}, 2),
    "peninsula_west": ({"文化", "建筑"}, 2),
    "cotai": ({"摄影", "休闲"}, 5),
}


def port_region_bias(port_id: str | None) -> str | None:
    port = get_port(port_id) if port_id else None
    return str(port.get("region_bias") or "") if port else None


def score_template_for_entry_port(template: dict, pref: Preference) -> tuple[int, list[str]]:
    """Boost templates whose theme fits the entry-port region."""
    bias = port_region_bias(pref.entry_port)
    if not bias:
        return 0, []
    themes, bonus = _REGION_THEME_BONUS.get(bias, (set(), 0))
    if bonus <= 0:
        return 0, []
    route_theme = str(template.get("theme") or "")
    template_id = str(template.get("id") or "")
    reasons: list[str] = []
    score = 0

    # 路氹模板彼此同权：不因「摄影 / 休闲」标签再拆分口岸加分。
    if "cotai" in template_id:
        if bias == "cotai":
            score += 4
            reasons.append("进境口岸靠近路氹，优先度假区模板")
        return score, reasons

    if themes and route_theme in themes:
        score += bonus
        reasons.append(f"进境口岸区域契合「{route_theme}」线")
    if bias.startswith("peninsula") and "cotai" not in template_id:
        score += 1
    return score, reasons


def events_for_preference(pref: Preference) -> list[dict]:
    travel = (pref.travel_date or "").strip() or date.today().isoformat()
    ports = {pid for pid in (pref.entry_port, pref.exit_port) if pid}
    matched: list[dict] = []
    for event in load_events():
        if str(event.get("date") or "") != travel:
            continue
        affected = set(event.get("affected_port_ids") or [])
        if ports & affected:
            matched.append(event)
            continue
        # Also surface if venue is on peninsula/cotai and user uses any related port later
        if not ports and event.get("crowd_level") in {"high", "medium"}:
            matched.append(event)
    return matched


def event_constraint_notes(pref: Preference) -> list[str]:
    notes: list[str] = []
    for event in events_for_preference(pref):
        note = str(event.get("note") or "").strip()
        name = str(event.get("name") or "大型活动")
        if note:
            notes.append(note)
        else:
            notes.append(f"当日有「{name}」，相关口岸／场馆周边可能较挤（估计，非实时排队）")
    return notes


def port_catalog() -> list[dict]:
    return load_ports()
