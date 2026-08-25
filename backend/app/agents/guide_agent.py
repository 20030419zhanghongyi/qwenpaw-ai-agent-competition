"""文化讲解 agent 封装（P2）。

职责：调用 QwenPaw ``guide`` agent，把一个澳门 POI 的文化资料（由 RAG 检索或精确取到）
+ 用户兴趣与语言，综合成**有据、可标来源、不编造**的沉浸式文化伴侣讲解。
**只讲解，不规划路线**，且**只以给定 POI 资料为事实依据**。

前提：guide agent 需在 QwenPaw Console 建（agent-id ``guide``，挂 ``macau-guide`` 技能，
挑已配的 text 模型），见 ``skills/README.md``。

失败哲学：任一环节（网络/解析/校验）失败返回 None，调用方据此降级，
保证 ``/guide/*`` 永不因 agent 抖动而 500。对齐 route/intent/photo 的纪律。
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings
from app.features.guide.models import ImmersiveGuide, NextExploration, ObservationItem

logger = logging.getLogger("macau_storywalk.guide_agent")

# QwenPaw 中文化讲解 agent 的 id（需手动在 Console 建，见 skills/README.md）
GUIDE_AGENT_ID = "guide"

_VALID_SOURCE_TYPE = {"official", "academic", "folklore", "ai"}
_VALID_LANGS = {"zh-CN", "zh-TW", "en", "pt"}
_CACHE_MAX_ENTRIES = 128
_cache: OrderedDict[tuple[Any, ...], tuple[float, "GuideExplanation"]] = OrderedDict()
_state_lock = threading.Lock()
_failure_until = 0.0


class GuideExplanation(BaseModel):
    """guide agent 输出（新 immersive + 伦理 source-attribution；兼容旧 flat text）。"""

    text: str = ""
    source_type: str = "ai"
    confidence: float = 0.0
    ai_generated: bool = True
    language: str = "zh-CN"
    immersive: ImmersiveGuide | None = None


def _build_prompt(
    poi: str,
    material: str,
    *,
    language: str,
    interests: list[str] | None,
    travel_type: list[str] | None = None,
    next_stop: str | None = None,
) -> str:
    """构造发给 guide agent 的 prompt（agent 自带 macau-guide 技能为 system prompt）。"""
    interest_str = "/".join(interests) if interests else "综合"
    travel_str = "/".join(travel_type) if travel_type else "未指定"
    next_line = (
        f"行程下一站：{next_stop.strip()}\n"
        if isinstance(next_stop, str) and next_stop.strip()
        else ("行程下一站：（本段末站）\n" if next_stop == "" else "")
    )
    language_instruction = {
        "zh-CN": "所有面向游客的字段必须只使用简体中文。",
        "zh-TW": "所有面向遊客的欄位必須只使用繁體中文。",
        "en": (
            "Translate the supplied Chinese source material and write every visitor-facing "
            "field entirely in natural English. Do not leave Chinese characters in titles, "
            "place names, observations, or narration."
        ),
        "pt": (
            "Traduza o material-fonte chinês e escreva todos os campos apresentados ao visitante "
            "inteiramente em português europeu. Não deixe caracteres chineses em títulos, nomes "
            "de locais, observações ou narração."
        ),
    }.get(language, "所有面向游客的字段必须使用指定语言。")
    return (
        f"POI：{poi or '（待识别）'}\n"
        f"语言：{language}\n"
        f"用户兴趣：{interest_str}\n"
        f"出行方式/同行：{travel_str}\n"
        f"{next_line}\n"
        f"语言硬性要求：{language_instruction}\n"
        "POI 文化资料（**仅以此为事实依据**，资料里没有的绝不补；"
        "管道：Location → POI → 下列资料 → 讲解）：\n"
        f"{material}\n\n"
        "请按 macau-guide 技能输出严格 JSON（首字符为 {，无解释、无代码围栏），"
        "包含沉浸式字段 title/subtitle/hook/why_it_matters/historical_story/"
        "things_to_observe/local_story/interactive_suggestion/next_exploration/audio_script，"
        "以及伦理字段 source_type/confidence/ai_generated/language；"
        "同时填 text（可与 audio_script 相同）供旧客户端。保持精炼：hook、why_it_matters、"
        "historical_story、local_story 各不超过两句，things_to_observe 只给 3 项，"
        "audio_script 不超过 220 个英文/葡文词或 450 个中文字符。"
    )


def _cache_key(
    poi: str,
    material: str,
    language: str,
    interests: list[str] | None,
    travel_type: list[str] | None,
    next_stop: str | None,
) -> tuple[Any, ...]:
    return (
        poi,
        material,
        language,
        tuple(interests or ()),
        tuple(travel_type or ()),
        next_stop,
    )


def _cached(key: tuple[Any, ...], now: float) -> GuideExplanation | None:
    with _state_lock:
        row = _cache.get(key)
        if row is None:
            return None
        created_at, value = row
        if now - created_at > settings.guide_agent_cache_ttl:
            _cache.pop(key, None)
            return None
        _cache.move_to_end(key)
        return value.model_copy(deep=True)


def _remember(key: tuple[Any, ...], value: GuideExplanation, now: float) -> None:
    global _failure_until
    with _state_lock:
        _failure_until = 0.0
        _cache[key] = (now, value.model_copy(deep=True))
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)


def _open_failure_circuit(now: float) -> None:
    global _failure_until
    with _state_lock:
        _failure_until = max(
            _failure_until,
            now + settings.guide_agent_failure_cooldown,
        )


def _circuit_is_open(now: float) -> bool:
    with _state_lock:
        return now < _failure_until


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 agent 文本里抽首个 {...} 并解析；失败返回 None（与 route/intent/photo 同款手法）。"""
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_observations(raw: Any) -> list[ObservationItem]:
    items: list[ObservationItem] = []
    if not isinstance(raw, list):
        return items
    for row in raw:
        if isinstance(row, str) and row.strip():
            items.append(ObservationItem(observation=row.strip(), explanation=""))
            continue
        if not isinstance(row, dict):
            continue
        obs = str(row.get("observation") or row.get("what") or "").strip()
        expl = str(row.get("explanation") or row.get("why") or "").strip()
        if obs:
            items.append(ObservationItem(observation=obs, explanation=expl))
    return items[:5]


def _parse_next(raw: Any) -> NextExploration:
    if not isinstance(raw, dict):
        return NextExploration()
    return NextExploration(
        location=str(raw.get("location") or "").strip(),
        distance=str(raw.get("distance") or "").strip(),
        walk_time=str(raw.get("walk_time") or raw.get("walk_min") or "").strip(),
        reason=str(raw.get("reason") or "").strip(),
    )


def _immersive_from_obj(obj: dict[str, Any], *, fallback_text: str, language: str) -> ImmersiveGuide:
    """从 agent JSON 抽 immersive；旧版仅有 text 时降级为最小结构。"""
    nested = obj.get("immersive") if isinstance(obj.get("immersive"), dict) else None
    src = nested or obj

    title = str(src.get("title") or obj.get("title") or "").strip()
    subtitle = str(src.get("subtitle") or obj.get("subtitle") or "").strip()
    hook = str(src.get("hook") or "").strip()
    why = str(src.get("why_it_matters") or src.get("why") or "").strip()
    hist = str(src.get("historical_story") or src.get("history") or "").strip()
    local = str(src.get("local_story") or src.get("story") or "").strip()
    interactive = str(src.get("interactive_suggestion") or "").strip()
    audio = str(src.get("audio_script") or obj.get("audio_script") or "").strip()
    observations = _parse_observations(
        src.get("things_to_observe") or src.get("observations")
    )
    next_ex = _parse_next(src.get("next_exploration") or src.get("next"))

    # Legacy-only agent: wrap flat text
    if not any((hook, why, hist, local, audio, observations)):
        body = fallback_text.strip()
        return ImmersiveGuide(
            title=title,
            subtitle=subtitle,
            hook=body,
            why_it_matters="",
            historical_story="",
            things_to_observe=[],
            local_story="",
            interactive_suggestion="",
            next_exploration=next_ex,
            audio_script=body,
        )

    if not audio:
        parts = [
            hook,
            why,
            hist,
            " ".join(
                f"{o.observation} {o.explanation}".strip() for o in observations
            ).strip(),
            local,
            interactive,
        ]
        if next_ex.location:
            parts.append(next_ex.location)
        audio = " ".join(p for p in parts if p).strip() if language in {"en", "pt"} else "".join(
            p for p in parts if p
        )

    return ImmersiveGuide(
        title=title,
        subtitle=subtitle,
        hook=hook,
        why_it_matters=why,
        historical_story=hist,
        things_to_observe=observations,
        local_story=local,
        interactive_suggestion=interactive,
        next_exploration=next_ex,
        audio_script=audio,
    )


def _coerce(obj: dict[str, Any]) -> GuideExplanation:
    """把 agent JSON 清洗成 GuideExplanation（容忍命名差异 / 缺字段 / 越界值）。"""
    text = str(obj.get("text") or obj.get("audio_script") or "").strip()

    source_type = obj.get("source_type")
    if not isinstance(source_type, str) or source_type.lower() not in _VALID_SOURCE_TYPE:
        source_type = "ai"
    else:
        source_type = source_type.lower()

    try:
        confidence = float(obj.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    language = obj.get("language")
    if not isinstance(language, str) or language not in _VALID_LANGS:
        language = "zh-CN"

    immersive = _immersive_from_obj(obj, fallback_text=text, language=language)
    if not text:
        text = immersive.audio_script
    elif not immersive.audio_script:
        immersive.audio_script = text

    return GuideExplanation(
        text=text,
        source_type=source_type,
        confidence=confidence,
        ai_generated=True,
        language=language,
        immersive=immersive,
    )


def generate(
    poi: str,
    *,
    material: str,
    language: str = "zh-CN",
    interests: list[str] | None = None,
    travel_type: list[str] | None = None,
    next_stop: str | None = None,
    client: QwenPawClient | None = None,
) -> GuideExplanation | None:
    """调 guide agent 生成讲解。任一环节失败返回 None（→ 调用方降级，讲解字段留空）。"""
    if not material.strip():
        return None
    managed_client = client is None
    now = time.monotonic()
    key = _cache_key(poi, material, language, interests, travel_type, next_stop)
    if managed_client:
        cached = _cached(key, now)
        if cached is not None:
            return cached
        if _circuit_is_open(now):
            logger.info("guide agent 熔断中，直接使用预设讲解")
            return None
        client = QwenPawClient(
            timeout=min(settings.qwenpaw_timeout, settings.guide_agent_max_duration)
        )
    try:
        ask_kwargs: dict[str, Any] = {
            "session_name": f"harness-guide-{uuid.uuid4().hex}",
        }
        if managed_client:
            ask_kwargs["max_duration"] = settings.guide_agent_max_duration
        text = client.ask(
            GUIDE_AGENT_ID,
            _build_prompt(
                poi,
                material,
                language=language,
                interests=interests,
                travel_type=travel_type,
                next_stop=next_stop,
            ),
            **ask_kwargs,
        )
    except QwenPawError as exc:
        if managed_client:
            _open_failure_circuit(time.monotonic())
        logger.info("guide agent 调用失败，降级：%s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 网络/流式响应任何意外都不抛穿，降级
        if managed_client:
            _open_failure_circuit(time.monotonic())
        logger.info("guide agent 异常，降级：%s", exc)
        return None

    obj = _extract_json(text)
    if obj is None:
        if managed_client:
            _open_failure_circuit(time.monotonic())
        logger.info("guide agent 输出非 JSON，降级。原文：%s", (text or "")[:200])
        return None
    try:
        result = _coerce(obj)
        if managed_client:
            _remember(key, result, time.monotonic())
        return result
    except (ValidationError, TypeError) as exc:
        if managed_client:
            _open_failure_circuit(time.monotonic())
        logger.info("guide agent 输出校验失败，降级：%s", exc)
        return None


def _build_ask_prompt(
    poi: str,
    question: str,
    material: str,
    *,
    language: str,
    input_language: str | None,
    interests: list[str] | None,
) -> str:
    interest_str = "/".join(interests) if interests else "综合"
    output_instruction = {
        "zh-CN": "只用自然、简洁的简体中文回答，不得夹杂英文、葡文或繁体中文。",
        "zh-TW": "只用自然、簡潔的繁體中文回答，不得夾雜英文、葡文或簡體中文。",
        "en": "Answer only in natural, concise English. Do not leave Chinese or Portuguese text in the answer.",
        "pt": "Responda apenas em português europeu natural e conciso. Não deixe texto chinês ou inglês na resposta.",
    }.get(language, "只使用指定的输出语言回答。")
    return (
        f"POI：{poi or '（待识别）'}\n"
        f"检测到的提问语言：{input_language or 'unknown'}\n"
        f"个人中心设定的回答语言：{language}\n"
        f"用户兴趣：{interest_str}\n\n"
        f"用户问题：{question}\n\n"
        "POI 文化资料与公开补充（**仅以此为事实依据**；含「联网公开资料」时必须优先用来回答，"
        "仍不够才明确说不知道，绝不编造）：\n"
        f"{material}\n\n"
        f"语言硬性要求：先理解提问原意，再{output_instruction}\n"
        "网页标题、资料原文和 POI 别名只作证据，不得把非目标语言原样混入答案。\n"
        "请用简洁口语回答用户问题，并按 macau-guide 技能输出严格 JSON"
        "（首字符为 {，无解释、无代码围栏）。追问场景可只填 "
        '{"text","audio_script","source_type","confidence","ai_generated","language"}；'
        "若能自然带出 hook/why_it_matters 等沉浸字段也可一并给出。"
    )


def answer(
    poi: str,
    question: str,
    *,
    material: str,
    language: str = "zh-CN",
    input_language: str | None = None,
    interests: list[str] | None = None,
    client: QwenPawClient | None = None,
) -> GuideExplanation | None:
    """就当前 POI 回答用户追问。失败返回 None，由调用方做资料摘录降级。"""
    if not material.strip() or not question.strip():
        return None
    client = client or QwenPawClient()
    try:
        text = client.ask(
            GUIDE_AGENT_ID,
            _build_ask_prompt(
                poi,
                question,
                material,
                language=language,
                input_language=input_language,
                interests=interests,
            ),
            # Keep follow-up answers isolated from both other answers and
            # full-guide generation sessions in the Console history.
            session_name=f"harness-guide-ask-{uuid.uuid4().hex}",
        )
    except QwenPawError as exc:
        logger.info("guide ask 调用失败，降级：%s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.info("guide ask 异常，降级：%s", exc)
        return None

    obj = _extract_json(text)
    if obj is None:
        logger.info("guide ask 输出非 JSON，降级。原文：%s", (text or "")[:200])
        return None
    try:
        return _coerce(obj)
    except (ValidationError, TypeError) as exc:
        logger.info("guide ask 输出校验失败，降级：%s", exc)
        return None


def translate_search_queries(
    question: str,
    *,
    input_language: str,
    client: QwenPawClient | None = None,
) -> dict[str, str]:
    """Translate only the search intent into supported retrieval languages.

    The result must never contain an answer or newly introduced facts. Failures
    return an empty mapping so the caller can use deterministic query fallbacks.
    """
    if not question.strip() or (client is None and not settings.guide_agent_enabled):
        return {}
    prompt = (
        "You are a multilingual search-query translator. Translate the user's question "
        "into concise search intent phrases in Simplified Chinese, English, and European "
        "Portuguese. Preserve names, dates, numbers, and the exact intent. Do not answer the "
        "question, add facts, explanations, or a POI name. Return strict JSON only with this "
        'shape: {"zh-CN":"...","en":"...","pt":"..."}.\n'
        f"Detected input language: {input_language}\n"
        f"Question: {question.strip()}"
    )
    try:
        raw = (client or QwenPawClient()).ask(
            GUIDE_AGENT_ID,
            prompt,
            session_name=f"guide-query-translate-{uuid.uuid4().hex}",
            max_duration=settings.guide_query_translation_max_duration,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("guide query 翻译失败，使用规则查询：%s", exc)
        return {}
    obj = _extract_json(raw)
    if not isinstance(obj, dict):
        logger.info("guide query 翻译不是 JSON，使用规则查询：%s", raw[:160])
        return {}
    translated: dict[str, str] = {}
    for language in ("zh-CN", "en", "pt"):
        value = str(obj.get(language) or "").strip()
        if value:
            translated[language] = value[:240]
    return translated
