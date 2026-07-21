"""路线匹配前的联网补充（接驳 / 主题游 / 当日节奏）。

复用 guide 的 ``search_web_multi``：短超时、失败降级为空列表。
输出写入 ``applied_constraints`` / 节点 note，辅助 POI 池排线解释，不替代规则排线。
离线 weights 权重已弱化；联网检索是动态信息的主要来源。
"""

from __future__ import annotations

import logging
import re

from app.models.user import Preference

from .poi_metadata import get_poi_metadata

logger = logging.getLogger("macau_storywalk.route_research")

# 本地已知接驳（不依赖网络也能给出口岸→路氹提示）
_PORT_TRANSFER_HINTS: dict[str, str] = {
    "poi_port_hengqin": (
        "横琴口岸至路氹度假区（威尼斯人／巴黎人等）不宜按步行排线："
        "出关后可乘澳门巴士或度假区穿梭巴士前往，建议预留 30–50 分钟通关与接驳"
    ),
    "poi_port_hzmb": (
        "港珠澳大桥口岸至路氹度假区建议乘巴士／穿梭巴士，"
        "勿按步行距离规划；预留通关与接驳时间"
    ),
    "poi_port_guanja": (
        "关闸口岸多通往澳门半岛北区；若当日主线在路氹，"
        "需预留巴士或轻轨接驳时间，不宜步行直达"
    ),
    "poi_port_qingmao": (
        "青茂口岸邻近半岛北区；前往路氹需巴士／轻轨接驳，勿按步行排线"
    ),
    "poi_port_outer_harbor": (
        "外港码头至路氹建议乘巴士或的士；半岛线则可接驳到历史城区"
    ),
}

_THEME_QUERY: dict[str, str] = {
    "cotai": "澳门路氹 度假区 一日游 穿梭巴士 景点",
    "heritage": "澳门历史城区 步行 一日游 大三巴 议事亭",
    "food": "澳门美食 一日游 小吃 街巷 推荐",
    "architecture": "澳门建筑 世遗 步行路线 教堂",
    "photo": "澳门摄影 打卡 花砖 旧街 镜头",
    "leisure": "澳门轻松散步 旧区 咖啡馆 少走路",
    "family": "澳门亲子 轻松行程 适合带小孩",
}

_INTEREST_QUERY: dict[str, str] = {
    "history": "澳门历史 旧区 世遗 导览",
    "culture": "澳门文化 中西交融 街巷",
    "food": "澳门必吃 美食 街区",
    "architecture": "澳门葡式建筑 教堂 花砖",
    "photo": "澳门拍照 打卡点 旧城",
}


def local_port_transfer_note(entry_port: str | None, first_poi_id: str | None = None) -> str | None:
    """Rule-based transfer tip for entry port → first stop."""
    port = (entry_port or "").strip()
    if not port:
        return None
    hint = _PORT_TRANSFER_HINTS.get(port)
    if not hint:
        meta = get_poi_metadata(port) or {}
        name = meta.get("name_zh") or port
        hint = f"{name}为行程起点；若下一站较远，请优先巴士／穿梭巴士，勿按步行排线"
    if first_poi_id:
        dest = get_poi_metadata(first_poi_id) or {}
        dest_name = dest.get("name_zh")
        if dest_name and dest_name not in hint:
            hint = f"{hint}（下一站：{dest_name}）"
    return hint


def _port_label(port_id: str | None) -> str:
    if not port_id:
        return ""
    from app.db.data import get_port

    port = get_port(port_id) or {}
    if port.get("name_zh"):
        return str(port["name_zh"])
    meta = get_poi_metadata(port_id) or {}
    return str(meta.get("name_zh") or meta.get("alias") or port_id)


def build_research_queries(pref: Preference) -> list[str]:
    """Build web queries for transfer, theme itineraries, and interest tips."""
    queries: list[str] = []
    entry = _port_label(pref.entry_port)
    themes = list(pref.themes or [])
    interests = list(pref.interests or [])

    if entry and "cotai" in themes:
        queries.append(f"{entry} 到 威尼斯人 巴士 穿梭巴士")
    elif entry:
        queries.append(f"澳门 {entry} 交通 巴士 接驳")

    for theme in themes[:3]:
        q = _THEME_QUERY.get(theme)
        if q and q not in queries:
            queries.append(q)

    for interest in interests[:2]:
        q = _INTEREST_QUERY.get(interest)
        if q and q not in queries:
            queries.append(q)

    if pref.duration == "multi-day":
        if "cotai" in themes:
            queries.append("澳门路氹 两日游 行程 威尼斯人 巴黎人")
        else:
            queries.append("澳门 两日游 行程安排 历史城区 美食")
    elif pref.duration == "half-day":
        queries.append("澳门 半日游 步行 精华 路线")
    elif "cotai" in themes and not any("路氹" in q for q in queries):
        queries.append("澳门路氹 度假区 穿梭巴士 接驳")

    if "less-walk" in (pref.physical or []) or "relax" in (pref.physical or []):
        queries.append("澳门 少走路 轻松 行程 巴士")

    # Deduplicate while preserving order; cap to keep latency bounded.
    deduped: list[str] = []
    for q in queries:
        if q not in deduped:
            deduped.append(q)
    return deduped[:5]


def _snippet_to_tip(snippet: str, *, max_len: int = 140) -> str | None:
    text = re.sub(r"\s+", " ", (snippet or "").strip())
    if len(text) < 20:
        return None
    keywords = (
        "巴士",
        "公交",
        "穿梭",
        "接驳",
        "通关",
        "口岸",
        "一日",
        "半日",
        "行程",
        "小时",
        "步行",
        "景点",
        "美食",
        "拍照",
        "打卡",
        "推荐",
        "shuttle",
        "bus",
        "walk",
        "itinerary",
    )
    if not any(k.lower() in text.lower() for k in keywords):
        return None
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return f"联网补充：{text}"


def research_route_tips(
    pref: Preference,
    *,
    language: str | None = None,
    enable_web: bool = True,
) -> list[str]:
    """Return short tips: local port transfer first, then optional web snippets."""
    tips: list[str] = []
    local = local_port_transfer_note(pref.entry_port)
    if local:
        tips.append(local)

    if not enable_web:
        return tips

    queries = build_research_queries(pref)
    if not queries:
        # Still attempt a generic Macau tip when preference is sparse.
        queries = ["澳门 旧区 步行 一日游 推荐"]

    try:
        from app.features.guide.web_search import search_web_multi

        hits = search_web_multi(
            queries,
            language=language or pref.language or "zh-CN",
            k=3,
            max_queries=min(4, len(queries)),
            budget_s=4.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("route research web search skipped: %s", exc)
        return tips

    for hit in hits:
        tip = _snippet_to_tip(hit.get("snippet") or "")
        if tip and tip not in tips:
            tips.append(tip)
        if len(tips) >= 6:
            break
    return tips
