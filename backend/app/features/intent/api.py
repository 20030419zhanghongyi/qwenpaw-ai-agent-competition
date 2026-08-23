"""需求理解接口（QwenPaw 需求理解 agent 驱动，规则版作 fallback）。

- ``INTENT_AGENT_ENABLED=true`` 且 intent agent 可用时：先调 agent 把自然语言翻成
  Preference（source="agent"）
- 否则降级规则版关键词解析（source="rules"），保证接口永不被 agent 抖动打穿
- ``/guide``：多轮偏好引导对话（AI 先提问），足够信息后返回 Preference
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.agents import intent_agent, preference_guide_agent
from app.agents.qwenpaw_client import QwenPawError
from app.core.config import settings
from app.guardrails.runtime import rate_limit, sanitize_untrusted_text
from app.models.user import SUPPORTED_LANGS, Preference, clamp_trip_days
from app.observability.trace import record_trace

logger = logging.getLogger("macau_storywalk.intent")

router = APIRouter(prefix="/api/v1/intent", tags=["intent"])

# 偏好引导 agent id 来自 preference_guide_agent 模块（pref-guide）。
# 与 intent agent 分工：intent 一次性解析已有文本，pref-guide 多轮对话逐步收集缺失信息。


class IntentParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        value = sanitize_untrusted_text(value)
        if not value:
            raise ValueError("text must not be blank")
        return value


class IntentGuideRequest(BaseModel):
    action: Literal["start", "message"] = "start"
    session_id: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=2000)
    language: str = "zh-CN"
    # 用户已发送的轮次（含本轮），供脚本 fallback 推进提问
    user_turn: int = Field(default=0, ge=0, le=40)
    # 累计用户原话（换行拼接），用于每轮软解析回填下方选项
    transcript: str | None = Field(default=None, max_length=8000)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = sanitize_untrusted_text(value)
        return value or None

    @field_validator("transcript")
    @classmethod
    def sanitize_transcript(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = sanitize_untrusted_text(value)
        return value or None

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value not in SUPPORTED_LANGS:
            return "zh-CN"
        return value


# --- 规则版 fallback：关键词扫描（保守，只认字面，语义留给 agent）---

_PHYS_LESS_WALK = ("不想太累", "少走", "轻松", "别太累", "走不动", "less walk", "not too tired")
_PHYS_NO_BACKTRACK = ("不要回头路", "别绕路", "顺路", "no backtrack", "one way")

_DUR_MULTI = (
    "多日",
    "几天",
    "两天",
    "三天",
    "兩天",
    "三天",
    "待几天",
    "待好幾天",
    "待好几天",
    "玩几天",
    "玩兩天",
    "玩两天",
    "2天",
    "3天",
    "multi-day",
    "multi day",
    "several days",
    "a few days",
    "dois dias",
    "vários dias",
    "varios dias",
)
_DUR_FULL = ("一整", "全天", "玩一天", "玩一整天", "full day", "whole day", "all day")
_DUR_EVENING = ("晚上", "夜间", "夜游", "夜景", "evening", "night")
_DUR_HALF = ("半天", "几小时", "下午", "上午", "half day", "half-day", "few hours")

_INTEREST_PHOTO = ("拍照", "摄影", "出片", "机位", "打卡", "photo", "photograph")
_INTEREST_FOOD = ("美食", "吃", "小吃", "葡挞", "茶餐厅", "甜品", "food", "snack")
_INTEREST_HISTORY = ("历史", "遗迹", "老街", "古迹", "history", "heritage")
_INTEREST_ARCH = ("建筑", "教堂", "牌坊", "庙", "architecture", "church")
_INTEREST_CULTURE = ("文化", "故事", "博物馆", "展览", "culture", "museum")

_TRAVEL_FAMILY = ("带老人", "带小孩", "亲子", "家庭", "一家", "长辈", "family", "kids", "parents")
_TRAVEL_SOLO = ("一个人", "独自", "自己", "单人", "solo", "alone")
_TRAVEL_FRIENDS = ("朋友", "情侣", "约会", "闺蜜", "两个人", "friends", "couple")
_TRAVEL_RELAX = ("休闲", "放松", "随便逛", "慢节奏", "relax", "slow")
_THEME_COTAI = (
    "路氹",
    "金光大道",
    "威尼斯人",
    "巴黎人",
    "伦敦人",
    "度假村",
    "赌场",
    "cotai",
    "casino",
    "venetian",
    "parisian",
)
_THEME_HERITAGE = ("历史城区", "旧城", "世遗", "heritage", "historic")
_THEME_FAMILY = ("亲子", "带小孩", "family theme")

# (keywords, poi_id) — order matters for first match
_PORT_ENTRIES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("关闸", "拱北", "portas do cerco", "gongbei", "border gate"), "poi_port_guanja"),
    (("青茂", "qingmao"), "poi_port_qingmao"),
    (("横琴", "hengqin"), "poi_port_hengqin"),
    (("港珠澳", "大桥口岸", "hzmb", "hong kong-zhuhai-macao"), "poi_port_hzmb"),
    (("外港", "outer harbour", "outer harbor", "港澳码头"), "poi_port_outer_harbor"),
    (("内港", "inner harbour", "inner harbor", "湾仔口岸"), "poi_0071"),
)


def _append_if_any(pref: Preference, text: str, keywords: tuple[str, ...], field: str, tag: str) -> None:
    lower = text.lower()
    if any(k.lower() in lower for k in keywords) and tag not in getattr(pref, field):
        getattr(pref, field).append(tag)


def _infer_ports(pref: Preference, text: str) -> None:
    """Map natural-language border mentions onto entry_port / exit_port."""
    lower = text.lower()
    found: list[str] = []
    for keywords, poi_id in _PORT_ENTRIES:
        if any(k.lower() in lower for k in keywords) and poi_id not in found:
            found.append(poi_id)

    if not found:
        return

    entry_cues = ("进", "入", "从", "入境", "arrive", "entry", "from ", "entrar")
    exit_cues = ("出", "离", "回", "出境", "leave", "exit", "depart", "sair")
    has_entry_cue = any(c in lower for c in entry_cues)
    has_exit_cue = any(c in lower for c in exit_cues)

    if len(found) == 1:
        poi_id = found[0]
        if has_exit_cue and not has_entry_cue:
            pref.exit_port = poi_id
        elif has_entry_cue and not has_exit_cue:
            pref.entry_port = poi_id
        else:
            # Ambiguous single mention: treat as entry (chips can refine exit)
            pref.entry_port = pref.entry_port or poi_id
        return

    # Multiple ports mentioned
    if has_entry_cue or has_exit_cue:
        # Prefer first as entry, last as exit when both present
        pref.entry_port = pref.entry_port or found[0]
        pref.exit_port = pref.exit_port or found[-1]
    else:
        pref.entry_port = pref.entry_port or found[0]
        pref.exit_port = pref.exit_port or found[-1]


def _infer_trip_days(text: str) -> int | None:
    """从「玩三天 / 2 days / dois dias」等短语抽出多日天数。"""
    t = (text or "").strip().lower()
    digit = re.search(r"([2-5])\s*[-]?\s*(?:天|日|days?|dias?)", t)
    if digit:
        return clamp_trip_days(int(digit.group(1)))
    word_map = {
        "两天": 2,
        "兩天": 2,
        "两日": 2,
        "兩日": 2,
        "两晚": 2,
        "兩晚": 2,
        "三天": 3,
        "三日": 3,
        "三晚": 3,
        "四天": 4,
        "四日": 4,
        "五天": 5,
        "五日": 5,
        "two days": 2,
        "dois dias": 2,
        "three days": 3,
        "três dias": 3,
        "tres dias": 3,
        "four days": 4,
        "quatro dias": 4,
        "five days": 5,
        "cinco dias": 5,
    }
    for phrase, days in word_map.items():
        if phrase in t or phrase in (text or ""):
            return clamp_trip_days(days)
    return None


def parse_intent_rules(text: str) -> Preference:
    """规则版 NL→Preference：关键词扫描（agent 不可用时的 fallback）。"""
    t = (text or "").strip()
    pref = Preference()  # 默认 duration=half-day, party_size=1, language=zh-CN

    trip_days = _infer_trip_days(t)
    if trip_days is not None:
        pref.duration = "multi-day"
        pref.trip_days = trip_days
    elif any(k.lower() in t.lower() for k in _DUR_MULTI):
        pref.duration = "multi-day"
    elif any(k.lower() in t.lower() for k in _DUR_FULL):
        pref.duration = "full-day"
    elif any(k.lower() in t.lower() for k in _DUR_EVENING):
        pref.duration = "evening"
    elif any(k.lower() in t.lower() for k in _DUR_HALF):
        pref.duration = "half-day"

    _append_if_any(pref, t, _PHYS_LESS_WALK, "physical", "less-walk")
    _append_if_any(pref, t, _PHYS_NO_BACKTRACK, "physical", "no-backtrack")

    _append_if_any(pref, t, _INTEREST_PHOTO, "interests", "photo")
    _append_if_any(pref, t, _INTEREST_FOOD, "interests", "food")
    _append_if_any(pref, t, _INTEREST_HISTORY, "interests", "history")
    _append_if_any(pref, t, _INTEREST_ARCH, "interests", "architecture")
    _append_if_any(pref, t, _INTEREST_CULTURE, "interests", "culture")

    _append_if_any(pref, t, _TRAVEL_FAMILY, "travel_type", "family")
    _append_if_any(pref, t, _TRAVEL_SOLO, "travel_type", "solo")
    _append_if_any(pref, t, _TRAVEL_FRIENDS, "travel_type", "friends")
    _append_if_any(pref, t, _TRAVEL_RELAX, "travel_type", "relax")

    _append_if_any(pref, t, _THEME_COTAI, "themes", "cotai")
    _append_if_any(pref, t, _THEME_HERITAGE, "themes", "heritage")
    _append_if_any(pref, t, _THEME_FAMILY, "themes", "family")

    _infer_ports(pref, t)
    return pref


_OPENERS: dict[str, str] = {
    "zh-CN": (
        "您好，欢迎使用澳迹同行。为了替您安排更合适的行程，"
        "想先请问您这次预计在澳门游览多久呢？可以选择半日、一日、多日，或夜间漫游。"
    ),
    "zh-TW": (
        "您好，歡迎使用澳跡同行。為了替您安排更合適的行程，"
        "想先請問您這次預計在澳門遊覽多久呢？可以選擇半日、一日、多日，或夜間漫遊。"
    ),
    "en": (
        "Welcome to Macau StoryWalk. To help us plan a trip that suits you, may I ask "
        "how long you would like to explore Macau this time: half a day, one day, "
        "multiple days, or an evening stroll?"
    ),
    "pt": (
        "Bem-vindo ao Macau StoryWalk. Para prepararmos um roteiro mais adequado, "
        "poderia dizer quanto tempo pretende explorar Macau desta vez: meio dia, um dia, "
        "vários dias ou um passeio noturno?"
    ),
}


# _guide_bootstrap_prompt / _extract_preference_json / _strip_json_for_display
# 已迁移到 backend/app/agents/preference_guide_agent.py，本文件不再维护内联 prompt。


def _preference_ready(pref: Preference) -> bool:
    """至少有兴趣或行走偏好或同行类型之一，才算可回填。"""
    return bool(pref.interests or pref.physical or pref.travel_type)


def _guide_with_qwenpaw(
    *,
    session_id: str,
    action: str,
    message: str | None,
    language: str,
    transcript: str | None = None,
) -> tuple[str, Preference | None, str]:
    """返回 (reply, preference|None, source).

    优先使用 pref-guide agent（多轮对话引导），不可用时返回空 reply 触发降级。
    """
    if not settings.preference_guide_agent_enabled:
        return ("", None, "script")

    reply, pref = preference_guide_agent.guide_step(
        session_id=session_id,
        action=action,
        message=message,
        language=language,
        transcript=transcript,
    )
    if not reply:
        # agent 调用失败 → 降级脚本
        return ("", None, "script")
    return (reply, pref, "agent")


def _merge_preferences(base: Preference, overlay: Preference) -> Preference:
    """增量合并：列表取并集；时长优先用 overlay（若 overlay 有明确非空信号）。"""
    travel = list(dict.fromkeys([*(base.travel_type or []), *(overlay.travel_type or [])]))
    interests = list(dict.fromkeys([*(base.interests or []), *(overlay.interests or [])]))
    physical = list(dict.fromkeys([*(base.physical or []), *(overlay.physical or [])]))
    # duration：overlay 有明确时长信号时采用
    if overlay.duration in {"full-day", "evening", "multi-day"}:
        duration = overlay.duration
    elif base.duration in {"full-day", "evening", "multi-day"} and overlay.duration == "half-day":
        duration = base.duration
    else:
        duration = overlay.duration or base.duration
    return Preference(
        duration=duration,
        party_size=max(base.party_size or 1, overlay.party_size or 1),
        travel_type=travel,
        interests=interests,
        themes=list(dict.fromkeys([*(base.themes or []), *(overlay.themes or [])])),
        physical=physical,
        language=overlay.language or base.language,
        entry_port=overlay.entry_port or base.entry_port,
        exit_port=overlay.exit_port or base.exit_port,
        travel_date=overlay.travel_date or base.travel_date,
        trip_days=overlay.trip_days if overlay.trip_days is not None else base.trip_days,
    )


def _soft_preference_from_transcript(transcript: str, language: str) -> Preference | None:
    """从累计用户话软解析；若完全没命中任何偏好信号则返回 None。"""
    if not (transcript or "").strip():
        return None
    soft = parse_intent_rules(transcript)
    soft.language = language
    # parse_intent_rules 默认 duration=half-day；用「是否命中关键词」判断有无信号
    hit = bool(
        soft.interests
        or soft.physical
        or soft.travel_type
        or soft.themes
        or soft.entry_port
        or soft.exit_port
    )
    lower = transcript.lower()
    duration_hit = any(
        k.lower() in lower
        for k in (*_DUR_MULTI, *_DUR_FULL, *_DUR_EVENING, *_DUR_HALF)
    )
    if not hit and not duration_hit:
        return None
    if not duration_hit:
        # 避免默认 half-day 覆盖用户已选手动选项：前端用 custom 哨兵
        soft.duration = "custom"
    return soft


def _guide_scripted_fallback(
    *,
    action: str,
    message: str | None,
    language: str,
    turn_count: int,
) -> tuple[str, Preference | None, str]:
    """QwenPaw 不可用时的脚本式引导（仍保持 AI-first 提问体验）。"""
    opener = _OPENERS.get(language, _OPENERS["zh-CN"])
    if action == "start":
        return opener, None, "script"

    pref = parse_intent_rules(message or "")
    pref.language = language

    followups = {
        "zh-CN": {
            "duration": "好的。你打算从哪个口岸进入澳门、从哪个口岸离开？例如关闸、青茂、横琴、港珠澳大桥或外港码头。",
            "ports": "记下了。那你是一个人，还是和朋友/家人一起？",
            "travel": "想多看哪一类？历史、建筑、美食、摄影，还是轻松逛逛？",
            "interest": "步行上有没有偏好？例如少走路、少爬坡、避免回头路。",
            "done": "明白了，我已记下你的偏好，可以点下方生成路线；也可继续补充。",
        },
        "zh-TW": {
            "duration": "好的。你打算從哪個口岸進入澳門、從哪個口岸離開？例如關閘、青茂、橫琴、港珠澳大橋或外港碼頭。",
            "ports": "記下了。那你是一個人，還是和朋友／家人一起？",
            "travel": "想多看哪一類？歷史、建築、美食、攝影，還是輕鬆逛逛？",
            "interest": "步行上有沒有偏好？例如少走路、少爬坡、避免回頭路。",
            "done": "明白了，我已記下你的偏好，可以點下方生成路線；也可繼續補充。",
        },
        "en": {
            "duration": "Got it. Which border will you enter Macau through, and which will you leave from — Gongbei, Qingmao, Hengqin, the HZMB port, or the Outer Harbour ferry?",
            "ports": "Noted. Are you solo, or with friends/family?",
            "travel": "What draws you most — history, architecture, food, photo, or a relaxed wander?",
            "interest": "Any walking preferences — less walking, fewer hills, or no backtracking?",
            "done": "Perfect — I’ve noted your preferences. You can generate a route below, or keep refining.",
        },
        "pt": {
            "duration": "Perfeito. Por que porto quer entrar em Macau e por qual sair — Portas do Cerco, Qingmao, Hengqin, ponte HKZM ou terminal do Porto Exterior?",
            "ports": "Anotado. Vai sozinho, ou com amigos/família?",
            "travel": "O que mais lhe interessa — história, arquitetura, comida, foto, ou um passeio calmo?",
            "interest": "Alguma preferência de caminhada — menos andar, menos subidas, ou sem voltar atrás?",
            "done": "Ótimo — anotei as preferências. Pode gerar o percurso abaixo, ou continuar a afinar.",
        },
    }
    copy = followups.get(language, followups["en"])

    if turn_count <= 1:
        return copy["duration"], pref if (pref.entry_port or pref.exit_port) else None, "script"
    if turn_count == 2:
        return copy["ports"], pref if (pref.entry_port or pref.exit_port or pref.travel_type) else None, "script"
    if turn_count == 3:
        return copy["travel"], None, "script"
    if turn_count == 4:
        return copy["interest"], None, "script"
    return copy["done"], pref if _preference_ready(pref) else pref, "script"


@router.post("/parse", dependencies=[Depends(rate_limit("text"))])
def parse(request: IntentParseRequest) -> dict:
    """自然语言 → 结构化 Preference（agent 先行，失败降级规则版）。"""
    source = "rules"
    pref = parse_intent_rules(request.text)

    if settings.intent_agent_enabled:
        agent_pref = intent_agent.parse_intent(request.text)
        if agent_pref is not None:
            pref = agent_pref
            source = "agent"
        else:
            logger.info("intent agent 不可用或解析失败，降级规则版")

    record_trace(
        kind="intent.parse",
        status=source,
        agent_id="intent" if source == "agent" else None,
        input_summary=request.text[:200],
    )
    return {"preference": pref.model_dump(), "source": source}


@router.post("/guide", dependencies=[Depends(rate_limit("text"))])
def guide(request: IntentGuideRequest) -> dict[str, Any]:
    """多轮偏好引导：AI 先提问，逐步确认后返回 Preference。"""
    if request.action == "message" and not (request.message or "").strip():
        return {
            "session_id": request.session_id or "",
            "reply": _OPENERS.get(request.language, _OPENERS["zh-CN"]),
            "ready": False,
            "preference": None,
            "source": "script",
            "error": "empty_message",
        }

    session_id = request.session_id or f"pref-guide-{uuid.uuid4().hex[:12]}"
    source = "script"
    reply = ""
    preference: Preference | None = None
    turn_count = request.user_turn or (1 if request.action == "message" else 0)

    try:
        reply, preference, source = _guide_with_qwenpaw(
            session_id=session_id,
            action=request.action,
            message=request.message,
            language=request.language,
            transcript=request.transcript,
        )
    except (QwenPawError, ValueError, Exception) as exc:  # noqa: BLE001
        logger.info("preference guide 降级脚本：%s", exc)
        reply, preference, source = _guide_scripted_fallback(
            action=request.action,
            message=request.message,
            language=request.language,
            turn_count=turn_count,
        )

    ready = False
    if preference is not None and source == "agent":
        ready = True
    elif preference is not None and source == "script" and _preference_ready(preference):
        ready = True

    # 每轮用累计 transcript 软解析，保证下方选项实时联动
    transcript = (request.transcript or request.message or "").strip()
    soft = _soft_preference_from_transcript(transcript, request.language)
    preview: Preference | None = preference
    if soft and preference:
        preview = _merge_preferences(soft, preference)
    elif soft:
        preview = soft
    elif preference:
        preview = preference

    record_trace(
        kind="intent.guide",
        status=source,
        agent_id=preference_guide_agent.PREF_GUIDE_AGENT_ID if source == "agent" else None,
        input_summary=(request.message or request.action)[:200],
        output_summary=reply[:200],
    )

    return {
        "session_id": session_id,
        "reply": reply,
        "ready": ready,
        "preference": preview.model_dump() if preview else None,
        "source": source,
    }
