"""需求理解接口（QwenPaw 需求理解 agent 驱动，规则版作 fallback）。

- ``INTENT_AGENT_ENABLED=true`` 且 intent agent 可用时：先调 agent 把自然语言翻成
  Preference（source="agent"）
- 否则降级规则版关键词解析（source="rules"），保证接口永不被 agent 抖动打穿
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.agents import intent_agent
from app.core.config import settings
from app.guardrails.runtime import rate_limit, sanitize_untrusted_text
from app.models.user import Preference
from app.observability.trace import record_trace

logger = logging.getLogger("macau_storywalk.intent")

router = APIRouter(prefix="/api/v1/intent", tags=["intent"])


class IntentParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        value = sanitize_untrusted_text(value)
        if not value:
            raise ValueError("text must not be blank")
        return value


# --- 规则版 fallback：关键词扫描（保守，只认字面，语义留给 agent）---

_PHYS_LESS_WALK = ("不想太累", "少走", "轻松", "别太累", "走不动")
_PHYS_NO_BACKTRACK = ("不要回头路", "别绕路", "顺路")

_DUR_FULL = ("一整", "全天", "玩一天", "玩一整天")
_DUR_EVENING = ("晚上", "夜间", "夜游", "夜景")
_DUR_HALF = ("半天", "几小时", "下午", "上午")

_INTEREST_PHOTO = ("拍照", "摄影", "出片", "机位", "打卡")
_INTEREST_FOOD = ("美食", "吃", "小吃", "葡挞", "茶餐厅", "甜品")
_INTEREST_HISTORY = ("历史", "遗迹", "老街", "古迹")
_INTEREST_ARCH = ("建筑", "教堂", "牌坊", "庙")
_INTEREST_CULTURE = ("文化", "故事", "博物馆", "展览")

_TRAVEL_FAMILY = ("带老人", "带小孩", "亲子", "家庭", "一家", "长辈")
_TRAVEL_SOLO = ("一个人", "独自", "自己", "单人")
_TRAVEL_FRIENDS = ("朋友", "情侣", "约会", "闺蜜", "两个人")
_TRAVEL_RELAX = ("休闲", "放松", "随便逛", "慢节奏")


def _append_if_any(pref: Preference, text: str, keywords: tuple[str, ...], field: str, tag: str) -> None:
    if any(k in text for k in keywords) and tag not in getattr(pref, field):
        getattr(pref, field).append(tag)


def parse_intent_rules(text: str) -> Preference:
    """规则版 NL→Preference：关键词扫描（agent 不可用时的 fallback）。"""
    t = (text or "").strip()
    pref = Preference()  # 默认 duration=half-day, party_size=1, language=zh-CN

    # duration（互斥，按显式程度排序）
    if any(k in t for k in _DUR_FULL):
        pref.duration = "full-day"
    elif any(k in t for k in _DUR_EVENING):
        pref.duration = "evening"
    elif any(k in t for k in _DUR_HALF):
        pref.duration = "half-day"

    # physical
    _append_if_any(pref, t, _PHYS_LESS_WALK, "physical", "less-walk")
    _append_if_any(pref, t, _PHYS_NO_BACKTRACK, "physical", "no-backtrack")

    # interests
    _append_if_any(pref, t, _INTEREST_PHOTO, "interests", "photo")
    _append_if_any(pref, t, _INTEREST_FOOD, "interests", "food")
    _append_if_any(pref, t, _INTEREST_HISTORY, "interests", "history")
    _append_if_any(pref, t, _INTEREST_ARCH, "interests", "architecture")
    _append_if_any(pref, t, _INTEREST_CULTURE, "interests", "culture")

    # travel_type
    _append_if_any(pref, t, _TRAVEL_FAMILY, "travel_type", "family")
    _append_if_any(pref, t, _TRAVEL_SOLO, "travel_type", "solo")
    _append_if_any(pref, t, _TRAVEL_FRIENDS, "travel_type", "friends")
    _append_if_any(pref, t, _TRAVEL_RELAX, "travel_type", "relax")

    return pref


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
