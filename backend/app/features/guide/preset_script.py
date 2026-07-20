"""预设讲解话术：用 POI 资料拼成结构化分段，再按兴趣做轻量个性化。

不调用 LLM，保证「听讲解」秒回；需要更深加工时可再走 guide agent 增强。
返回 ``sections``（概览 / 历史 / 建筑观察 / 故事动线）供前端图文分段展示，
同时保留拼接后的 ``text`` 供 TTS 与旧客户端。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

# 兴趣 → 优先强调的分段 id（在对应段前加一句引导）
_INTEREST_SECTION: dict[str, str] = {
    "photo": "architecture",
    "architecture": "architecture",
    "history": "history",
    "culture": "history",
    "food": "story",
    "relax": "overview",
}

_OPENERS = {
    "zh-CN": "我们现在来到{name}。",
    "zh-TW": "我們現在來到{name}。",
    "en": "We've arrived at {name}.",
    "pt": "Chegámos a {name}.",
}

_FOCUS_HINTS = {
    "zh-CN": {
        "photo": "如果你想拍照，可以留意这些细节：",
        "architecture": "建筑上值得多看一眼：",
        "history": "这段历史沿革值得细听：",
        "culture": "从文化角度说：",
        "food": "和吃喝逛有关的一点：",
        "relax": "慢慢走的话，可以这样感受：",
    },
    "zh-TW": {
        "photo": "如果想拍照，可以留意這些細節：",
        "architecture": "建築上值得多看一眼：",
        "history": "這段歷史沿革值得細聽：",
        "culture": "從文化角度說：",
        "food": "和吃喝逛有關的一點：",
        "relax": "慢慢走的話，可以這樣感受：",
    },
    "en": {
        "photo": "For photos, look for:",
        "architecture": "Architecturally,",
        "history": "Here's how the place evolved:",
        "culture": "Culturally,",
        "food": "For food lovers,",
        "relax": "At an easy pace,",
    },
    "pt": {
        "photo": "Para fotos, repare em:",
        "architecture": "Na arquitetura,",
        "history": "Eis a evolução deste lugar:",
        "culture": "Do ponto de vista cultural,",
        "food": "Para quem gosta de comida,",
        "relax": "Num ritmo calmo,",
    },
}

_CLOSERS = {
    "zh-CN": "若你还想了解附近其他地标，可以在讲解页继续搜索。",
    "zh-TW": "若你還想了解附近其他地標，可以在講解頁繼續搜尋。",
    "en": "If you’d like another landmark story, you can keep browsing on the Guide page.",
    "pt": "Se quiser outra história próxima, continue a explorar na página Guia.",
}

_CLOSERS_NEXT = {
    "zh-CN": "想继续听，我们可以走向下一站「{next}」。",
    "zh-TW": "想繼續聽，我們可以走向下一站「{next}」。",
    "en": "When you’re ready, we can walk on to the next stop: {next}.",
    "pt": "Quando quiser, seguimos para a próxima paragem: {next}.",
}


_CLOSERS_END = {
    "zh-CN": "这一站已是本段行程的收尾，慢慢走、慢慢看就好。",
    "zh-TW": "這一站已是本段行程的收尾，慢慢走、慢慢看就好。",
    "en": "This is the last stop on this stretch — take your time here.",
    "pt": "Esta é a última paragem deste troço — vá com calma.",
}


def _closer(language: str, next_stop: str | None) -> str:
    lang = language if language in _CLOSERS else "zh-CN"
    if next_stop is None:
        return _CLOSERS[lang]
    name = next_stop.strip()
    if not name:
        return _CLOSERS_END[lang]
    return _CLOSERS_NEXT[lang].format(next=name)


@lru_cache
def _load_pois() -> tuple[dict, ...]:
    candidates = [
        Path(settings.data_dir) / "pois.json",
        Path("/app/data/pois.json"),
        Path("/app/backend/../data/pois.json").resolve(),
    ]
    for path in candidates:
        if path.exists():
            return tuple(json.loads(path.read_text(encoding="utf-8")).get("pois", []))
    return ()


def _find_poi(query: str) -> dict | None:
    name = (query or "").strip()
    if not name:
        return None
    pois = _load_pois()
    for p in pois:
        if name in {
            p.get("name_zh"),
            p.get("name_en"),
            p.get("name_pt"),
            p.get("id"),
            p.get("alias"),
        }:
            return p
    for p in pois:
        nz = str(p.get("name_zh") or "")
        if nz and (name in nz or nz in name):
            return p
    return None


def _join_parts(parts: list[str], lang: str) -> str:
    cleaned = [p.strip() for p in parts if p and str(p).strip()]
    if not cleaned:
        return ""
    if lang in {"en", "pt"}:
        return " ".join(cleaned)
    return "".join(cleaned)


def _section(section_id: str, body: str) -> dict[str, str] | None:
    text = (body or "").strip()
    if not text:
        return None
    return {"id": section_id, "body": text}


def build_preset_narration(
    poi_query: str,
    *,
    language: str = "zh-CN",
    interests: list[str] | None = None,
    next_stop: str | None = None,
) -> dict | None:
    """返回预设讲解 dict；找不到 POI 则 None。

    ``next_stop``：行程下一站名称；空字符串表示已是末站；``None`` 表示无行程上下文。

    结构化字段：
    - ``sections``: ``[{id, body}, ...]``，id ∈ overview|history|architecture|story
    - ``text``: 各段拼接，供 TTS / 旧客户端
    """
    poi = _find_poi(poi_query)
    if not poi:
        return None

    lang = language if language in _OPENERS else "zh-CN"
    name = (
        (poi.get("name_en") if lang in {"en", "pt"} and poi.get("name_en") else None)
        or poi.get("name_zh")
        or poi.get("name_en")
        or poi_query
    )

    interests = [i for i in (interests or []) if i]
    primary = interests[0] if interests else None
    focus_hint = _FOCUS_HINTS.get(lang, {}).get(primary or "") if primary else None
    focus_section = _INTEREST_SECTION.get(primary or "") if primary else None

    intro = str(poi.get("intro") or "").strip()
    history = str(poi.get("history") or "").strip()
    architecture = str(poi.get("architecture") or "").strip()
    observation = str(poi.get("observation_tips") or "").strip()
    story = str(poi.get("story") or "").strip()

    overview_parts = [_OPENERS[lang].format(name=name)]
    if intro:
        overview_parts.append(intro)
    elif not history and not architecture:
        overview_parts.append(str(name))

    # 历史段：完整 history；若缺失则用 architecture 中的沿革信息作弱补充（仍标为 history）
    history_body = history
    if not history_body and architecture and any(
        marker in architecture
        for marker in ("年", "世纪", "世紀", "built", "século", "seculo", "原为", "原為", "曾")
    ):
        history_body = architecture

    arch_parts: list[str] = []
    if architecture and architecture != history_body:
        arch_parts.append(architecture)
    if observation:
        arch_parts.append(observation)

    story_parts: list[str] = []
    if story:
        story_parts.append(story)
    story_parts.append(_closer(lang, next_stop))

    raw_sections: list[tuple[str, str]] = [
        ("overview", _join_parts(overview_parts, lang)),
        ("history", history_body),
        ("architecture", _join_parts(arch_parts, lang)),
        ("story", _join_parts(story_parts, lang)),
    ]

    sections: list[dict[str, str]] = []
    for section_id, body in raw_sections:
        text = body.strip()
        if not text:
            continue
        if focus_hint and focus_section == section_id:
            text = _join_parts([focus_hint, text], lang)
        item = _section(section_id, text)
        if item:
            sections.append(item)

    if not sections:
        sections = [{"id": "overview", "body": _OPENERS[lang].format(name=name)}]

    text = _join_parts([s["body"] for s in sections], lang)

    source_type = str(poi.get("source_type") or "official")
    if source_type not in {"official", "academic", "folklore", "ai"}:
        source_type = "official"

    return {
        "text": text,
        "sections": sections,
        "source_type": source_type,
        "confidence": 0.85,
        "ai_generated": False,
        "language": lang,
        "source": "preset",
        "poi_name": name,
        "poi_id": str(poi.get("id") or ""),
        "next_stop": (next_stop.strip() if isinstance(next_stop, str) else None),
        "blocked": False,
        "error": None,
        "review": {
            "decision": "skip",
            "source": "preset",
            "issues": [],
            "reviewer_notes": "preset script",
        },
    }
