"""需求理解 agent 封装。

职责：调用 QwenPaw `intent` agent，把用户的自然语言出行需求翻成**结构化 Preference**。
**不配对、不排线** —— 把 Preference 交回后端配对引擎（`match_routes`）执行。

与 route_agent 的区别：route_agent 输出的是对既有 Preference 的**增量调整**
（RouteAdjustment），本 agent 从零**生成**初始 Preference，故输出即最终 Preference，
无需 apply_* 步骤。

失败哲学：任何环节（网络/解析/校验）失败都返回 None，调用方据此降级到规则版，
保证 `/intent/parse` 永不因 agent 抖动而 500。对齐 route_agent 的纪律。
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from pydantic import ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.models.user import Preference, SUPPORTED_LANGS

logger = logging.getLogger("macau_storywalk.intent_agent")

# QwenPaw 中需求理解 agent 的 id（需手动在 Console 建，见 skills/README.md）
INTENT_AGENT_ID = "intent"

# Preference 合法取值（与 models/user.py 对齐），用于校验/清洗 agent 输出
_VALID_INTERESTS = {"history", "architecture", "food", "photo", "culture"}
_VALID_PHYSICAL = {"normal", "less-walk", "no-backtrack"}
_VALID_DURATION = {"half-day", "full-day", "evening", "multi-day", "custom"}
_VALID_TRAVEL_TYPE = {"solo", "friends", "family", "relax"}
_VALID_LANGS = set(SUPPORTED_LANGS)
_VALID_PORTS = {
    "poi_port_guanja",
    "poi_port_qingmao",
    "poi_port_hengqin",
    "poi_port_hzmb",
    "poi_port_outer_harbor",
    "poi_0071",
}
_VALID_STORIES = {"lotus_city_double_map", "taipa_letters", "coloane_after_tide"}


def _build_prompt(text: str) -> str:
    """构造发给 intent agent 的 prompt（agent 自带 requirement-understand 技能为 system prompt）。"""
    return (
        "用户出行需求：" + text.strip() + "\n\n"
        "请按 requirement-understand 技能输出严格 JSON（首字符为 {，无解释、无代码围栏）。"
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 agent 文本里抽首个 {...} 并解析；失败返回 None。"""
    if not text:
        return None
    # 优先尝试整体解析（agent 理想输出就是纯 JSON）
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # 兜底：抓首个平衡的 {...}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _clean_list(values: Any, valid: set[str]) -> list[str]:
    """过滤白名单 + 去重。"""
    if not isinstance(values, list):
        return []
    seen: list[str] = []
    for v in values:
        if isinstance(v, str) and v in valid and v not in seen:
            seen.append(v)
    return seen


def _coerce(obj: dict[str, Any]) -> Preference:
    """把 agent 的 JSON 清洗成 Preference（容忍命名差异，丢未知值，回落默认）。"""
    duration = obj.get("duration")
    if not isinstance(duration, str) or duration not in _VALID_DURATION:
        duration = "half-day"  # 与 Preference 默认值一致

    language = obj.get("language")
    if not isinstance(language, str) or language not in _VALID_LANGS:
        language = "zh-CN"

    party_size = obj.get("party_size")
    if not isinstance(party_size, int) or party_size < 1:
        party_size = 1

    entry_port = obj.get("entry_port")
    if not isinstance(entry_port, str) or entry_port not in _VALID_PORTS:
        entry_port = None
    exit_port = obj.get("exit_port")
    if not isinstance(exit_port, str) or exit_port not in _VALID_PORTS:
        exit_port = None
    travel_date = obj.get("travel_date")
    if not isinstance(travel_date, str) or len(travel_date) < 8:
        travel_date = None

    trip_days = obj.get("trip_days")
    if not isinstance(trip_days, int):
        trip_days = None
    story_opt_in = obj.get("story_opt_in")
    if not isinstance(story_opt_in, bool):
        story_opt_in = None
    story_id = obj.get("story_id")
    if story_id not in _VALID_STORIES:
        story_id = None
    story_day = obj.get("story_day")
    if not isinstance(story_day, int) or not 1 <= story_day <= 5:
        story_day = None
    story_selections = obj.get("story_selections")
    if not isinstance(story_selections, list):
        story_selections = []
    # Preference validator clamps / drops invalid values

    return Preference(
        duration=duration,
        party_size=party_size,
        travel_type=_clean_list(obj.get("travel_type"), _VALID_TRAVEL_TYPE),
        interests=_clean_list(obj.get("interests"), _VALID_INTERESTS),
        physical=_clean_list(obj.get("physical"), _VALID_PHYSICAL),
        language=language,
        entry_port=entry_port,
        exit_port=exit_port,
        travel_date=travel_date,
        trip_days=trip_days,
        story_opt_in=story_opt_in,
        story_id=story_id,
        story_day=story_day,
        story_selections=story_selections,
    )


def parse_intent(text: str, *, client: QwenPawClient | None = None) -> Preference | None:
    """调 intent agent 解析需求。任一环节失败返回 None（→ 调用方降级规则版）。"""
    client = client or QwenPawClient()
    try:
        reply = client.ask(
            INTENT_AGENT_ID,
            _build_prompt(text),
            session_id=f"harness-intent-{uuid.uuid4().hex}",
            session_name="harness-intent",
        )
    except QwenPawError as exc:
        logger.info("intent agent 调用失败，降级规则版：%s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 网络/流式响应/传输层任何意外都不抛穿，降级规则版
        logger.info("intent agent 调用异常，降级规则版：%s", exc)
        return None

    obj = _extract_json(reply)
    if obj is None:
        logger.info("intent agent 输出非 JSON，降级规则版。原文：%s", (reply or "")[:200])
        return None

    try:
        return _coerce(obj)
    except (ValidationError, TypeError) as exc:
        logger.info("intent agent 输出校验失败，降级规则版：%s", exc)
        return None
