"""路线微调 agent 封装（P1）。

职责：调用 QwenPaw `route` agent，把自然语言偏好翻成**结构化意图**（RouteAdjustment）。
**不排线** —— 把意图交回后端规则引擎（`adjust_route` / `construct_route`）执行。

失败哲学：任何环节（网络/解析/校验）失败都返回 None，调用方据此降级到规则版，
保证 `/routes/adjust` 永不因 agent 抖动而 500。对齐 plan §C。
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.models.user import Preference

logger = logging.getLogger("macau_storywalk.route_agent")

# QwenPaw 中路线 agent 的 id（需手动在 Console 建，见 skills/README.md）
ROUTE_AGENT_ID = "route"

# Preference 合法取值（与 models/user.py 对齐），用于校验/清洗 agent 输出
_VALID_INTERESTS = {"history", "architecture", "food", "photo", "culture"}
_VALID_PHYSICAL = {"normal", "less-walk", "no-backtrack"}
_VALID_DURATION = {"half-day", "full-day", "evening", "custom"}


class RouteAdjustment(BaseModel):
    """路线 agent 输出的结构化意图。"""

    preference_add_interests: list[str] = Field(default_factory=list)
    preference_add_physical: list[str] = Field(default_factory=list)
    preference_add_duration: str | None = None
    add_nodes: list[str] = Field(default_factory=list)
    remove_tail: bool = False
    reorder_by_district: bool = False
    notes: str = ""


def is_actionable(adjustment: RouteAdjustment) -> bool:
    """Return whether the parsed result contains an executable route change."""
    return bool(
        adjustment.preference_add_interests
        or adjustment.preference_add_physical
        or adjustment.preference_add_duration
        or adjustment.add_nodes
        or adjustment.remove_tail
        or adjustment.reorder_by_district
    )


def _build_prompt(instruction: str, preference: Preference, route_id: str) -> str:
    """构造发给 route agent 的 prompt（agent 自带 route-adjust 技能为 system prompt）。"""
    return (
        "当前用户偏好：" + json.dumps(preference.model_dump(), ensure_ascii=False) + "\n"
        "当前路线模板 id：" + route_id + "\n"
        "用户调整指令：" + instruction.strip() + "\n\n"
        "请按 route-adjust 技能输出严格 JSON（首字符为 {，无解释、无代码围栏）。"
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


def _coerce(obj: dict[str, Any]) -> RouteAdjustment:
    """把 agent 的 JSON 字段名映射/清洗成 RouteAdjustment（容忍命名差异）。"""
    pref = obj.get("preference_add") if isinstance(obj.get("preference_add"), dict) else {}

    def _clean(values: Any, valid: set[str]) -> list[str]:
        if not isinstance(values, list):
            return []
        seen: list[str] = []
        for v in values:
            if isinstance(v, str) and v in valid and v not in seen:
                seen.append(v)
        return seen

    duration = pref.get("duration")
    if not isinstance(duration, str) or duration not in _VALID_DURATION:
        duration = None

    return RouteAdjustment(
        preference_add_interests=_clean(pref.get("interests"), _VALID_INTERESTS),
        preference_add_physical=_clean(pref.get("physical"), _VALID_PHYSICAL),
        preference_add_duration=duration,
        add_nodes=[n for n in (obj.get("add_nodes") or []) if n in ("photo", "food")],
        remove_tail=bool(obj.get("remove_tail", False)),
        reorder_by_district=bool(obj.get("reorder_by_district", False)),
        notes=str(obj.get("notes", ""))[:200],
    )


def parse_route_adjustment(
    instruction: str,
    preference: Preference,
    route_id: str,
    *,
    client: QwenPawClient | None = None,
) -> RouteAdjustment | None:
    """调 route agent 解析意图。任一环节失败返回 None（→ 调用方降级规则版）。"""
    client = client or QwenPawClient()
    try:
        text = client.ask(
            ROUTE_AGENT_ID,
            _build_prompt(instruction, preference, route_id),
            session_id=f"harness-route-{uuid.uuid4().hex}",
            session_name="harness-route",
        )
    except QwenPawError as exc:
        logger.info("route agent 调用失败，降级规则版：%s", exc)
        return None

    obj = _extract_json(text)
    if obj is None:
        logger.info("route agent 输出非 JSON，降级规则版。原文：%s", (text or "")[:200])
        return None

    try:
        return _coerce(obj)
    except (ValidationError, TypeError) as exc:
        logger.info("route agent 输出校验失败，降级规则版：%s", exc)
        return None


def apply_adjustment_to_preference(pref: Preference, adjustment: RouteAdjustment) -> Preference:
    """把 agent 意图叠加到 Preference（新增项去重），供现有排线引擎消费。"""
    updated = pref.model_copy(deep=True)
    interests = [
        *adjustment.preference_add_interests,
        *adjustment.add_nodes,
    ]
    for interest in interests:
        if interest not in updated.interests:
            updated.interests.append(interest)
    physical_preferences = list(adjustment.preference_add_physical)
    if adjustment.remove_tail:
        physical_preferences.append("less-walk")
    if adjustment.reorder_by_district:
        physical_preferences.append("no-backtrack")
    for physical in physical_preferences:
        if physical not in updated.physical:
            updated.physical.append(physical)
    if adjustment.preference_add_duration:
        updated.duration = adjustment.preference_add_duration
    return updated
