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
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.features.guide.models import ImmersiveGuide, NextExploration, ObservationItem

logger = logging.getLogger("macau_storywalk.guide_agent")

# QwenPaw 中文化讲解 agent 的 id（需手动在 Console 建，见 skills/README.md）
GUIDE_AGENT_ID = "guide"

_VALID_SOURCE_TYPE = {"official", "academic", "folklore", "ai"}
_VALID_LANGS = {"zh-CN", "zh-TW", "en", "pt"}


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
    return (
        f"POI：{poi or '（待识别）'}\n"
        f"语言：{language}\n"
        f"用户兴趣：{interest_str}\n"
        f"出行方式/同行：{travel_str}\n"
        f"{next_line}\n"
        "POI 文化资料（**仅以此为事实依据**，资料里没有的绝不补；"
        "管道：Location → POI → 下列资料 → 讲解）：\n"
        f"{material}\n\n"
        "请按 macau-guide 技能输出严格 JSON（首字符为 {，无解释、无代码围栏），"
        "包含沉浸式字段 title/subtitle/hook/why_it_matters/historical_story/"
        "things_to_observe/local_story/interactive_suggestion/next_exploration/audio_script，"
        "以及伦理字段 source_type/confidence/ai_generated/language；"
        "同时填 text（可与 audio_script 相同）供旧客户端。"
    )


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
    client = client or QwenPawClient()
    try:
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
            session_name="harness-guide",
        )
    except QwenPawError as exc:
        logger.info("guide agent 调用失败，降级：%s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 网络/流式响应任何意外都不抛穿，降级
        logger.info("guide agent 异常，降级：%s", exc)
        return None

    obj = _extract_json(text)
    if obj is None:
        logger.info("guide agent 输出非 JSON，降级。原文：%s", (text or "")[:200])
        return None
    try:
        return _coerce(obj)
    except (ValidationError, TypeError) as exc:
        logger.info("guide agent 输出校验失败，降级：%s", exc)
        return None


def _build_ask_prompt(
    poi: str,
    question: str,
    material: str,
    *,
    language: str,
    interests: list[str] | None,
) -> str:
    interest_str = "/".join(interests) if interests else "综合"
    return (
        f"POI：{poi or '（待识别）'}\n"
        f"语言：{language}\n"
        f"用户兴趣：{interest_str}\n\n"
        f"用户问题：{question}\n\n"
        "POI 文化资料与公开补充（**仅以此为事实依据**；含「联网公开资料」时必须优先用来回答，"
        "仍不够才明确说不知道，绝不编造）：\n"
        f"{material}\n\n"
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
                poi, question, material, language=language, interests=interests
            ),
            session_name="harness-guide-ask",
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
