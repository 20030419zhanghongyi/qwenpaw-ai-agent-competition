"""预设讲解话术：用 POI 资料即时拼接，再按兴趣做轻量个性化。

不调用 LLM，保证「听讲解」秒回；需要更深加工时可再走 guide agent 增强。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

# 兴趣 → 优先选用的 POI 字段顺序
_INTEREST_FIELDS: dict[str, tuple[str, ...]] = {
    "photo": ("observation_tips", "architecture", "intro", "story"),
    "architecture": ("architecture", "history", "intro", "observation_tips"),
    "history": ("history", "story", "intro", "architecture"),
    "culture": ("intro", "history", "story", "architecture"),
    "food": ("story", "intro", "observation_tips", "history"),
    "relax": ("intro", "observation_tips", "story", "history"),
}

_DEFAULT_FIELDS = ("intro", "history", "architecture", "story", "observation_tips")

_OPENERS = {
    "zh-CN": "我们现在来到{name}。",
    "zh-TW": "我們現在來到{name}。",
    "en": "We've arrived at {name}. Here's a short story about this place.",
    "pt": "Chegámos a {name}. Aqui vai uma breve história deste lugar.",
}

_FOCUS_HINTS = {
    "zh-CN": {
        "photo": "如果你想拍照，可以留意这些细节：",
        "architecture": "建筑上值得多看一眼：",
        "history": "这段历史很有意思：",
        "culture": "从文化角度说：",
        "food": "和吃喝逛有关的一点：",
        "relax": "慢慢走的话，可以这样感受：",
    },
    "zh-TW": {
        "photo": "如果想拍照，可以留意這些細節：",
        "architecture": "建築上值得多看一眼：",
        "history": "這段歷史很有意思：",
        "culture": "從文化角度說：",
        "food": "和吃喝逛有關的一點：",
        "relax": "慢慢走的話，可以這樣感受：",
    },
    "en": {
        "photo": "For photos, look for:",
        "architecture": "Architecturally,",
        "history": "Historically,",
        "culture": "Culturally,",
        "food": "For food lovers,",
        "relax": "At an easy pace,",
    },
    "pt": {
        "photo": "Para fotos, repare em:",
        "architecture": "Na arquitetura,",
        "history": "Historicamente,",
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


def _field_order(interests: list[str] | None) -> list[str]:
    if not interests:
        return list(_DEFAULT_FIELDS)
    ordered: list[str] = []
    for interest in interests:
        for field in _INTEREST_FIELDS.get(interest, ()):
            if field not in ordered:
                ordered.append(field)
    for field in _DEFAULT_FIELDS:
        if field not in ordered:
            ordered.append(field)
    return ordered


def _pick_sentences(text: str, limit: int = 2) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    normalized = raw.replace("！", "。").replace("!", "。").replace("？", "。").replace("?", "。")
    parts = [p.strip() for p in normalized.split("。") if p.strip()]
    if not parts:
        return raw
    joined = "。".join(parts[:limit])
    return joined if joined.endswith("。") else joined + "。"


def build_preset_narration(
    poi_query: str,
    *,
    language: str = "zh-CN",
    interests: list[str] | None = None,
    next_stop: str | None = None,
) -> dict | None:
    """返回预设讲解 dict；找不到 POI 则 None。

    ``next_stop``：行程下一站名称；空字符串表示已是末站；``None`` 表示无行程上下文。
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
    order = _field_order(interests)

    parts: list[str] = [_OPENERS[lang].format(name=name)]
    if primary:
        hint = _FOCUS_HINTS.get(lang, {}).get(primary)
        if hint:
            parts.append(hint)

    used = 0
    for field in order:
        value = str(poi.get(field) or "").strip()
        if not value:
            continue
        limit = 3 if used == 0 else 2
        piece = _pick_sentences(value, limit=limit)
        if piece:
            parts.append(piece)
            used += 1
        if used >= 3:
            break

    if used == 0:
        parts.append(str(poi.get("intro") or name))

    parts.append(_closer(lang, next_stop))
    if lang in {"en", "pt"}:
        text = " ".join(p.strip() for p in parts if p.strip())
    else:
        text = "".join(p.strip() for p in parts if p.strip())

    source_type = str(poi.get("source_type") or "official")
    if source_type not in {"official", "academic", "folklore", "ai"}:
        source_type = "official"

    return {
        "text": text,
        "source_type": source_type,
        "confidence": 0.85,
        "ai_generated": False,
        "language": lang,
        "source": "preset",
        "poi_name": name,
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
