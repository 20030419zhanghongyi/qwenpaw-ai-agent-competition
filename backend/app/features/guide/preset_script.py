"""预设讲解话术：用 POI 资料拼成沉浸式文化伴侣结构。

不调用 LLM，保证「听讲解」秒回；需要更深加工时可再走 guide agent 增强。

返回：
- ``immersive``：新结构化陪伴式讲解（hook / why / story / observe / next…）
- ``sections``：legacy 概览/历史/建筑/故事，供旧客户端
- ``text`` / ``audio_script``：拼接口语稿，供 TTS
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.features.guide.models import ImmersiveGuide, NextExploration, ObservationItem

# 兴趣 → 优先强调的分段 id（legacy sections 前加引导）
_INTEREST_SECTION: dict[str, str] = {
    "photo": "architecture",
    "architecture": "architecture",
    "history": "history",
    "culture": "history",
    "food": "story",
    "relax": "overview",
    "family": "story",
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
        "family": "如果是和家人同行，可以这样一起看：",
    },
    "zh-TW": {
        "photo": "如果想拍照，可以留意這些細節：",
        "architecture": "建築上值得多看一眼：",
        "history": "這段歷史沿革值得細聽：",
        "culture": "從文化角度說：",
        "food": "和吃喝逛有關的一點：",
        "relax": "慢慢走的話，可以這樣感受：",
        "family": "如果是和家人同行，可以這樣一起看：",
    },
    "en": {
        "photo": "For photos, look for:",
        "architecture": "Architecturally,",
        "history": "Here's how the place evolved:",
        "culture": "Culturally,",
        "food": "For food lovers,",
        "relax": "At an easy pace,",
        "family": "With family, try this together:",
    },
    "pt": {
        "photo": "Para fotos, repare em:",
        "architecture": "Na arquitetura,",
        "history": "Eis a evolução deste lugar:",
        "culture": "Do ponto de vista cultural,",
        "food": "Para quem gosta de comida,",
        "relax": "Num ritmo calmo,",
        "family": "Em família, experimente isto:",
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

_OBS_WHY_DEFAULT = {
    "zh-CN": "这是现场最容易错过、却最能读懂此地气质的细节。",
    "zh-TW": "這是現場最容易錯過、卻最能讀懂此地氣質的細節。",
    "en": "Easy to miss on site — and one of the best clues to this place’s character.",
    "pt": "Fácil de passar ao lado — e uma das melhores pistas do carácter deste lugar.",
}

_INTERACTIVE = {
    "zh-CN": {
        "photo": "试着找一个能同时收入建筑轮廓与脚下地面纹理的角度，拍一张「此刻的澳门」。",
        "architecture": "走近一点，用手（不触摸文物）比划一下立面比例，感受中西尺度如何并置。",
        "history": "停三十秒，想象这里几十年前的人流与今天的游客如何重叠。",
        "culture": "问问自己：眼前哪一处细节最像「澳门混杂」的日常？",
        "food": "若附近有老店或茶档，把这一站的味道也记进行程。",
        "family": "和同行的人各找一个最喜欢的细节，互相讲一句为什么。",
        "relax": "找个能坐下的角落，先听环境声再看建筑，会更有感觉。",
        "default": "选一个你最想记住的细节，用一句话记在手机备忘录里。",
    },
    "zh-TW": {
        "photo": "試著找一個能同時收入建築輪廓與腳下地面紋理的角度，拍一張「此刻的澳門」。",
        "architecture": "走近一點，用手（不觸摸文物）比劃一下立面比例，感受中西尺度如何並置。",
        "history": "停三十秒，想像這裡幾十年前的人流與今天的遊客如何重疊。",
        "culture": "問問自己：眼前哪一處細節最像「澳門混雜」的日常？",
        "food": "若附近有老店或茶檔，把這一站的味道也記進行程。",
        "family": "和同行的人各找一個最喜歡的細節，互相講一句為什麼。",
        "relax": "找個能坐下的角落，先聽環境聲再看建築，會更有感覺。",
        "default": "選一個你最想記住的細節，用一句話記在手機備忘錄裡。",
    },
    "en": {
        "photo": "Find a frame that holds both the façade and the ground pattern — one shot of Macau right now.",
        "architecture": "Step closer and trace the proportions with your eye (no touching) — East and West side by side.",
        "history": "Pause for thirty seconds and picture the crowds of decades past overlapping today’s visitors.",
        "culture": "Ask yourself: which detail here feels most like everyday Macau hybrid life?",
        "food": "If an old tea house or snack stall is nearby, fold that taste into this stop.",
        "family": "Each person picks a favorite detail and says one sentence about why.",
        "relax": "Sit somewhere quiet — listen first, then look — the place lands better that way.",
        "default": "Pick one detail you want to keep, and jot a single sentence in your notes.",
    },
    "pt": {
        "photo": "Procure um enquadramento com a fachada e o padrão do chão — um retrato de Macau agora.",
        "architecture": "Aproxime-se e leia as proporções com o olhar (sem tocar) — Oriente e Ocidente lado a lado.",
        "history": "Pare trinta segundos e imagine as multidões de há décadas sobrepostas às de hoje.",
        "culture": "Pergunte-se: que detalhe aqui parece mais o quotidiano híbrido de Macau?",
        "food": "Se houver uma casa de chá ou petiscos perto, junte esse sabor a esta paragem.",
        "family": "Cada um escolhe um pormenor favorito e diz uma frase sobre o porquê.",
        "relax": "Sente-se num canto — ouça primeiro, depois olhe — o lugar chega melhor assim.",
        "default": "Escolha um detalhe para guardar e anote uma única frase.",
    },
}

_NEXT_REASON = {
    "zh-CN": "和这里同属一条可走文化动线，故事可以接着往下听。",
    "zh-TW": "和這裡同屬一條可走文化動線，故事可以接著往下聽。",
    "en": "It continues this walkable cultural thread — the story can keep going.",
    "pt": "Continua este fio cultural a pé — a história pode seguir.",
}

_NEXT_REASON_END = {
    "zh-CN": "这一段行程到此收束，可在讲解页再搜附近地标。",
    "zh-TW": "這一段行程到此收束，可在講解頁再搜附近地標。",
    "en": "This stretch ends here — browse nearby landmarks on the Guide page if you like.",
    "pt": "Este troço termina aqui — explore outros pontos na página Guia se quiser.",
}

_GAMBLING_CAUTION = {
    "zh-CN": "若附近涉及娱乐场区域，请勿参与赌博，注意风险。",
    "zh-TW": "若附近涉及娛樂場區域，請勿參與賭博，注意風險。",
    "en": "If you are near a casino area, please do not gamble — mind the risks.",
    "pt": "Perto de zonas de casino, não jogue — tenha em mente os riscos.",
}

_GAMBLING_RE = re.compile(
    r"赌场|賭場|casino|gambling|博彩|赌厅|賭廳|娱乐场(?!所)|娛樂場(?!所)",
    re.IGNORECASE,
)

_CLAUSE_SPLIT = re.compile(r"[；;。！!？?\n]+")
# Soft splits for architecture / tips when hard sentence breaks are scarce
_SOFT_SPLIT = re.compile(r"[，、,]+")

_HOOK_BRIDGE = {
    "zh-CN": "先停一下，感受脚下的地面与四周的立面。",
    "zh-TW": "先停一下，感受腳下的地面與四周的立面。",
    "en": "Pause for a moment — feel the ground underfoot and the façades around you.",
    "pt": "Pare um momento — sinta o chão sob os pés e as fachadas em volta.",
}

_WHY_BRIDGE = {
    "zh-CN": "它在澳门城市记忆里的位置，可以这样理解：",
    "zh-TW": "它在澳門城市記憶裡的位置，可以這樣理解：",
    "en": "In Macau’s urban memory, it sits like this:",
    "pt": "Na memória urbana de Macau, situa-se assim:",
}

_STORY_PAST = {
    "zh-CN": "过去，",
    "zh-TW": "過去，",
    "en": "In the past, ",
    "pt": "No passado, ",
}

_STORY_TODAY = {
    "zh-CN": "今日，",
    "zh-TW": "今日，",
    "en": "Today, ",
    "pt": "Hoje, ",
}

_LOCAL_BRIDGE = {
    "zh-CN": "本地人与过客共享这片开放空间：",
    "zh-TW": "本地人與過客共享這片開放空間：",
    "en": "Locals and visitors share this open space:",
    "pt": "Locais e visitantes partilham este espaço aberto:",
}

_INTERACTIVE_EXTRA = {
    "zh-CN": "把眼前最打动你的一处细节，用一句话记下来，离开后也还能想起这里的气质。",
    "zh-TW": "把眼前最打動你的一處細節，用一句話記下來，離開後也還能想起這裡的氣質。",
    "en": "Jot one detail that stays with you — a single sentence you’ll still remember later.",
    "pt": "Anote um detalhe que fique consigo — uma frase que ainda lembre depois.",
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


def _first_sentence(text: str, *, max_len: int = 120) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    for sep in ("。", "！", "？", ".", "!", "?"):
        if sep in raw:
            head = raw.split(sep, 1)[0].strip()
            if head:
                return (head + (sep if sep in "。！？" else sep))[:max_len]
    return raw[:max_len]


def _split_clauses(text: str, *, soft: bool = False) -> list[str]:
    parts = [p.strip() for p in _CLAUSE_SPLIT.split(text or "") if p and p.strip()]
    if soft and len(parts) < 3:
        soft_parts: list[str] = []
        for part in parts or [str(text or "").strip()]:
            if not part:
                continue
            chunks = [c.strip() for c in _SOFT_SPLIT.split(part) if c and c.strip()]
            if len(chunks) >= 2:
                soft_parts.extend(chunks)
            else:
                soft_parts.append(part)
        # Prefer soft chunks only when they meaningfully expand the list
        if len(soft_parts) > len(parts):
            parts = soft_parts
    return [p for p in parts if len(p) >= 4]


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _compose_hook(name: str, intro: str, *, lang: str) -> str:
    opener = _OPENERS[lang].format(name=name)
    bridge = _HOOK_BRIDGE.get(lang, _HOOK_BRIDGE["zh-CN"])
    lead = _first_sentence(intro, max_len=140) or name
    # Avoid repeating the opener's name-only feel when intro already names the place
    return _join_parts([opener, bridge, lead], lang)


def _compose_why(intro: str, opener: str, *, lang: str, focus_hint: str | None) -> str:
    bridge = _WHY_BRIDGE.get(lang, _WHY_BRIDGE["zh-CN"])
    body = (intro or "").strip() or opener
    parts = [bridge, body]
    if focus_hint:
        parts = [focus_hint, *parts]
    return _join_parts(parts, lang)


def _compose_historical_story(
    history: str,
    story: str,
    intro: str,
    *,
    lang: str,
    focus_hint: str | None = None,
) -> str:
    """Past → (light) transformation → today, only from available fields."""
    past = (history or "").strip()
    today_src = (story or "").strip() or (intro or "").strip()
    if not past and not today_src:
        return ""

    past_label = _STORY_PAST.get(lang, _STORY_PAST["zh-CN"])
    today_label = _STORY_TODAY.get(lang, _STORY_TODAY["zh-CN"])

    # Split multi-sentence history into past + transformation when possible
    hist_sentences = [
        s.strip()
        for s in re.split(r"(?<=[。！？.!?])\s*", past)
        if s and s.strip()
    ]
    # Drop trailing empties from split
    hist_sentences = [s for s in hist_sentences if s]
    transform_body = ""
    past_body = past
    if len(hist_sentences) >= 2:
        # Last history sentence often carries "今日/现在" — keep with past/transform,
        # and prefer story field for the spoken "today" beat when available.
        if any(
            hist_sentences[-1].startswith(p)
            for p in ("今日", "今天", "如今", "时至今日", "時至今日", "Today", "Hoje")
        ):
            if len(hist_sentences) >= 3:
                past_body = _join_parts(hist_sentences[:-2], lang)
                transform_body = hist_sentences[-2]
                # Fold the history's "today" into today_src only if story is empty
                if not (story or "").strip():
                    today_src = hist_sentences[-1]
            else:
                past_body = hist_sentences[0]
                transform_body = ""
                if not (story or "").strip():
                    today_src = hist_sentences[-1]
        else:
            past_body = hist_sentences[0]
            transform_body = _join_parts(hist_sentences[1:], lang)

    chunks: list[str] = []
    if past_body:
        if lang in {"en", "pt"}:
            chunks.append(f"{past_label}{past_body}")
        else:
            if past_body.startswith(("过去", "過去", "从前", "從前", "因曾", "因")):
                chunks.append(past_body)
            else:
                chunks.append(f"{past_label}{past_body}")

    if transform_body and transform_body not in (past_body or ""):
        chunks.append(transform_body)

    if today_src and today_src != past and today_src != past_body:
        today_body = today_src
        # Prefer the present-day sentence when story has multiple beats
        today_sentences = [
            s.strip()
            for s in re.split(r"(?<=[。！？.!?])\s*", today_src)
            if s and s.strip()
        ]
        presentish = [
            s
            for s in today_sentences
            if any(
                m in s
                for m in (
                    "时至今日",
                    "時至今日",
                    "今日",
                    "今天",
                    "如今",
                    "平日",
                    "Today",
                    "Hoje",
                )
            )
        ]
        if presentish:
            today_body = _join_parts(presentish, lang)
        for prefix in ("时至今日，", "時至今日，", "今日，", "今天，", "Today, ", "Hoje, "):
            if today_body.startswith(prefix):
                today_body = today_body[len(prefix) :].strip()
                break
        if today_body and today_body not in past and today_body not in (past_body or ""):
            # Avoid "今日，今日…" when body already leads with 今日/今天
            if today_body.startswith(("今日", "今天", "如今", "Today", "Hoje")):
                chunks.append(today_body)
            else:
                chunks.append(f"{today_label}{today_body}")

    hist = _join_parts(chunks, lang) if chunks else past or today_src
    if focus_hint and hist:
        hist = _join_parts([focus_hint, hist], lang)
    return hist


def _compose_local_story(story: str, *, lang: str) -> str:
    body = (story or "").strip()
    if not body:
        return ""
    bridge = _LOCAL_BRIDGE.get(lang, _LOCAL_BRIDGE["zh-CN"])
    return _join_parts([bridge, body], lang)


_TIP_CAVEAT = re.compile(
    r"(以现场为准|以現場為準|subject to (?:conditions|weather)|conforme ao local)",
    re.IGNORECASE,
)


def _split_tip_caveat(tip: str) -> tuple[str, str]:
    """Return (actionable tip, trailing caveat) without inventing facts."""
    raw = (tip or "").strip()
    if not raw:
        return "", ""
    m = _TIP_CAVEAT.search(raw)
    if not m:
        return raw, ""
    before = raw[: m.start()]
    # Keep "具体人流与天气以现场为准" as one caveat unit when comma-separated
    comma = max(before.rfind("，"), before.rfind(","), before.rfind("；"), before.rfind(";"))
    if comma >= 8:
        return before[:comma].strip(), raw[comma + 1 :].strip()
    head = before.rstrip("，、,;； ")
    if len(head) >= 8:
        return head, raw[m.start() :].strip()
    # Entire tip is essentially a caveat
    return "", raw


def _punctuate_join(parts: list[str], lang: str) -> str:
    """Join Chinese clauses ensuring a sentence break between chunks."""
    cleaned = [p.strip() for p in parts if p and str(p).strip()]
    if not cleaned:
        return ""
    if lang in {"en", "pt"}:
        return " ".join(cleaned)
    out = cleaned[0]
    for part in cleaned[1:]:
        if out.endswith(("。", "！", "？", ".", "!", "?", "；", ";")):
            out += part
        else:
            out += "。" + part
    return out


def _build_observations(
    architecture: str,
    observation_tips: str,
    *,
    lang: str,
    focus_hint: str | None = None,
) -> list[ObservationItem]:
    # Soft-split façades; keep tip sentences intact (hard clauses only)
    arch_parts = _dedupe_keep_order(_split_clauses(architecture, soft=True))
    tip_parts = _dedupe_keep_order(_split_clauses(observation_tips, soft=False))
    why_default = _OBS_WHY_DEFAULT.get(lang, _OBS_WHY_DEFAULT["zh-CN"])
    tip_expl: list[str] = []
    tip_caveats: list[str] = []
    for tip in tip_parts:
        action, caveat = _split_tip_caveat(tip)
        if action:
            tip_expl.append(action)
        if caveat:
            tip_caveats.append(caveat)
    tip_expl = _dedupe_keep_order(tip_expl)
    tip_caveats = _dedupe_keep_order(tip_caveats)
    items: list[ObservationItem] = []

    if arch_parts:
        for i, obs in enumerate(arch_parts[:5]):
            expl = tip_expl[i] if i < len(tip_expl) else (tip_expl[-1] if tip_expl else why_default)
            if tip_caveats and i == 0:
                expl = _punctuate_join([expl, tip_caveats[0]], lang)
            if focus_hint and i == 0:
                obs = _join_parts([focus_hint, obs], lang)
            items.append(ObservationItem(observation=obs, explanation=expl))
        # Extra tip sentences only when we still have fewer than 3 observe rows
        if len(items) < 3:
            for tip in tip_expl[len(arch_parts) :]:
                if len(items) >= 5:
                    break
                items.append(ObservationItem(observation=tip, explanation=why_default))
    elif tip_expl:
        for i, tip in enumerate(tip_expl[:5]):
            obs = _join_parts([focus_hint, tip], lang) if focus_hint and i == 0 else tip
            expl = tip_caveats[0] if tip_caveats and i == 0 else why_default
            items.append(ObservationItem(observation=obs, explanation=expl))

    return items[:5]


def _interactive_for(
    lang: str,
    interests: list[str],
    travel_type: list[str] | None,
) -> str:
    table = _INTERACTIVE.get(lang, _INTERACTIVE["zh-CN"])
    keys = list(interests or [])
    for tt in travel_type or []:
        if tt in {"family", "solo", "couple", "friends"} and tt not in keys:
            keys.append(tt)
    primary = table["default"]
    for key in keys:
        if key in table:
            primary = table[key]
            break
    extra = _INTERACTIVE_EXTRA.get(lang, _INTERACTIVE_EXTRA["zh-CN"])
    return _join_parts([primary, extra], lang)


def _subtitle_for(poi: dict, lang: str, intro: str) -> str:
    themes = poi.get("theme") or []
    if isinstance(themes, list) and themes:
        label = " · ".join(str(t) for t in themes[:3] if t)
        if lang in {"en", "pt"} and poi.get("name_en"):
            return label
        return label
    return _first_sentence(intro, max_len=48)


def _is_gambling_related(poi: dict, name: str) -> bool:
    hay = " ".join(
        str(x or "")
        for x in (
            name,
            poi.get("name_zh"),
            poi.get("name_en"),
            poi.get("alias"),
            (poi.get("amap") or {}).get("type"),
            (poi.get("amap") or {}).get("address"),
        )
    )
    return bool(_GAMBLING_RE.search(hay))


def _legacy_sections_from_immersive(
    immersive: ImmersiveGuide,
    *,
    lang: str,
    next_stop: str | None,
) -> list[dict[str, str]]:
    """Map immersive fields back to overview|history|architecture|story for old clients."""
    overview = _join_parts(
        [p for p in (immersive.hook, immersive.why_it_matters) if p],
        lang,
    )
    history = immersive.historical_story
    arch = _join_parts(
        [
            _join_parts([o.observation, o.explanation], lang)
            for o in immersive.things_to_observe
        ],
        lang,
    )
    story = _join_parts(
        [
            immersive.local_story,
            immersive.interactive_suggestion,
            _closer(lang, next_stop),
        ],
        lang,
    )
    raw = [
        ("overview", overview),
        ("history", history),
        ("architecture", arch),
        ("story", story),
    ]
    sections: list[dict[str, str]] = []
    for section_id, body in raw:
        item = _section(section_id, body)
        if item:
            sections.append(item)
    if not sections:
        sections = [{"id": "overview", "body": immersive.title or immersive.hook or ""}]
    return sections


def build_preset_narration(
    poi_query: str,
    *,
    language: str = "zh-CN",
    interests: list[str] | None = None,
    next_stop: str | None = None,
    travel_type: list[str] | None = None,
    next_distance: str | None = None,
    next_walk_time: str | None = None,
) -> dict | None:
    """返回预设讲解 dict；找不到 POI 则 None。

    ``next_stop``：行程下一站名称；空字符串表示已是末站；``None`` 表示无行程上下文。
    ``next_distance`` / ``next_walk_time``：可选，来自行程腿信息（有则写入 next_exploration）。

    结构化字段：
    - ``immersive``: 新文化伴侣 JSON
    - ``sections``: ``[{id, body}, ...]``，id ∈ overview|history|architecture|story
    - ``text``: 与 ``audio_script`` 相同，供 TTS / 旧客户端
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

    # 历史段：完整 history；若缺失则用 architecture 中的沿革信息作弱补充（仍不编造）
    history_body = history
    if not history_body and architecture and any(
        marker in architecture
        for marker in ("年", "世纪", "世紀", "built", "século", "seculo", "原为", "原為", "曾")
    ):
        history_body = architecture

    opener = _OPENERS[lang].format(name=name)
    hook = _compose_hook(name, intro, lang=lang)
    why = _compose_why(
        intro,
        opener,
        lang=lang,
        focus_hint=focus_hint if focus_section == "overview" else None,
    )

    hist_story = _compose_historical_story(
        history_body,
        story,
        intro,
        lang=lang,
        focus_hint=focus_hint if focus_section == "history" else None,
    )

    observe_focus = focus_hint if focus_section == "architecture" else None
    observations = _build_observations(
        architecture if architecture != history_body else "",
        observation,
        lang=lang,
        focus_hint=observe_focus,
    )
    # If architecture was reused as history, still surface observation tips
    if not observations and architecture and architecture == history_body:
        observations = _build_observations(
            "",
            observation or architecture,
            lang=lang,
            focus_hint=observe_focus,
        )

    interactive = _interactive_for(lang, interests, travel_type)
    if _is_gambling_related(poi, str(name)):
        interactive = _join_parts(
            [interactive, _GAMBLING_CAUTION.get(lang, _GAMBLING_CAUTION["zh-CN"])],
            lang,
        )

    local_story = _compose_local_story(story, lang=lang)

    next_loc = ""
    next_reason = ""
    if next_stop is None:
        next_loc = ""
        next_reason = ""
    elif not str(next_stop).strip():
        next_loc = ""
        next_reason = _NEXT_REASON_END.get(lang, _NEXT_REASON_END["zh-CN"])
    else:
        next_loc = str(next_stop).strip()
        next_reason = _NEXT_REASON.get(lang, _NEXT_REASON["zh-CN"])

    next_exploration = NextExploration(
        location=next_loc,
        distance=(next_distance or "").strip(),
        walk_time=(next_walk_time or "").strip(),
        reason=next_reason,
    )

    observe_audio = _join_parts(
        [
            _join_parts([o.observation, o.explanation], lang)
            for o in observations
        ],
        lang,
    )
    next_audio = ""
    if next_exploration.location:
        next_audio = _closer(lang, next_exploration.location)
    elif next_stop is not None:
        next_audio = _closer(lang, next_stop)

    audio_parts = [
        hook,
        why if why != hook else "",
        hist_story,
        observe_audio,
        local_story,
        interactive,
        next_audio,
    ]
    audio_script = _join_parts(audio_parts, lang)

    immersive = ImmersiveGuide(
        title=str(name),
        subtitle=_subtitle_for(poi, lang, intro),
        hook=hook,
        why_it_matters=why,
        historical_story=hist_story,
        things_to_observe=observations,
        local_story=local_story,
        interactive_suggestion=interactive,
        next_exploration=next_exploration,
        audio_script=audio_script,
    )

    sections = _legacy_sections_from_immersive(
        immersive,
        lang=lang,
        next_stop=next_stop,
    )
    if not sections:
        sections = [{"id": "overview", "body": opener}]

    # Prefer audio_script; keep text identical for TTS / legacy
    text = audio_script or _join_parts([s["body"] for s in sections], lang)

    source_type = str(poi.get("source_type") or "official")
    if source_type not in {"official", "academic", "folklore", "ai"}:
        source_type = "official"

    return {
        "text": text,
        "audio_script": immersive.audio_script or text,
        "immersive": immersive.to_public_dict(),
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
