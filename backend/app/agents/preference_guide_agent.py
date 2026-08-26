"""偏好引导 agent 封装。

职责：调用 QwenPaw `pref-guide` agent，通过多轮对话逐步收集用户旅行偏好，
收集足够信息后输出结构化 Preference JSON。

与 intent_agent 的区别：intent_agent 是一次性解析（NL → Preference），
本 agent 是多轮对话引导（发现缺失 → 提问 → 收集 → 够了再输出 Preference）。

失败哲学：任何环节（网络/解析/校验）失败都返回 (reply, None)，
调用方据此降级到脚本版，保证 /intent/guide 永不因 agent 抖动而 500。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.models.user import Preference, SUPPORTED_LANGS

logger = logging.getLogger("macau_storywalk.pref_guide_agent")

# QwenPaw 中偏好引导 agent 的 id（需手动在 Console 建，见 skills/README.md）
PREF_GUIDE_AGENT_ID = "pref-guide"

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


def _build_prompt(
    *,
    action: str,
    message: str | None,
    language: str,
    transcript: str | None = None,
) -> str:
    """构造发给 pref-guide agent 的消息。

    action="start" 时不带用户消息，agent 根据技能 system prompt 自行发起开场提问。
    action="message" 时把用户消息发给 agent 继续对话。
    transcript 为累计用户原话，帮助 agent 理解已讨论过的内容。
    """
    if action == "start":
        return (
            f"[Language: reply ONLY in `{language}`]\n"
            "开始偏好引导对话。请礼貌欢迎用户，并询问本次在澳门的游览时长。"
            "问题必须明确列出半日、一日、多日和夜间漫游四个选项；不要只问‘今天’，"
            "因为用户可能计划多日行程。"
        )

    user_text = (message or "").strip()
    parts = [f"[Language: reply ONLY in `{language}`]"]
    if transcript and transcript.strip():
        parts.append(f"对话历史摘要：{transcript.strip()[:3000]}")
    parts.append(f"用户说：{user_text}")
    parts.append(
        "在结束引导前必须确认用户是否参加故事路线；参加则确认三选一的 story_id，"
        "多日行程还必须确认 story_day。未确认时继续礼貌追问，不要输出最终 JSON。"
    )
    return "\n".join(parts)


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
        duration = "half-day"

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
    )


def _strip_json_for_display(text: str) -> str:
    """聊天气泡里去掉尾部 JSON，只留自然语言。"""
    if not text:
        return text
    match = re.search(r"\{[\s\S]*\}\s*$", text.strip())
    if not match:
        return text.strip()
    cleaned = text[: match.start()].strip()
    return cleaned or text.strip()


def guide_step(
    *,
    session_id: str,
    action: str,
    message: str | None,
    language: str,
    transcript: str | None = None,
    client: QwenPawClient | None = None,
) -> tuple[str, Preference | None]:
    """执行一轮偏好引导对话。

    Returns:
        (reply_text, preference_or_none)
        - reply_text: agent 的自然语言回复（或含尾部 JSON 的原始文本）
        - preference_or_none: 如果本轮 agent 输出了 Preference JSON 则返回，否则 None

    任一环节失败返回 (fallback_reply, None)，调用方据此降级到脚本版。
    """
    client = client or QwenPawClient()
    try:
        raw_reply = client.ask(
            PREF_GUIDE_AGENT_ID,
            _build_prompt(
                action=action,
                message=message,
                language=language,
                transcript=transcript,
            ),
            session_id=session_id,
            session_name="pref-guide",
        )
    except QwenPawError as exc:
        logger.info("pref-guide agent 调用失败，降级脚本版：%s", exc)
        return ("", None)
    except Exception as exc:  # noqa: BLE001
        logger.info("pref-guide agent 调用异常，降级脚本版：%s", exc)
        return ("", None)

    # 尝试从回复中提取 Preference JSON
    pref = _extract_preference(raw_reply, language)
    if pref is not None:
        return (_strip_json_for_display(raw_reply), pref)

    # 没有 JSON → 这轮只是提问，继续对话
    return (raw_reply.strip(), None)


def _extract_preference(text: str, language: str) -> Preference | None:
    """从 agent 回复中提取并校验 Preference JSON。"""
    obj = _extract_json(text)
    if obj is None:
        return None
    try:
        pref = _coerce(obj)
        pref.language = language
        return pref
    except (ValidationError, TypeError) as exc:
        logger.info("pref-guide agent 输出校验失败：%s", exc)
        return None
