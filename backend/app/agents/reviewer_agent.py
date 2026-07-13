"""独立审核 agent 封装。

职责：调用 QwenPaw `reviewer` agent，对讲解/路线/文案等「待上线内容」做合规与安全审核，
输出结构化裁定 `ReviewVerdict`（pass / revise / block + issues）。

设计纪律（对齐 content-safety-review 技能）：**审核者只审核、不改写正文** ——
改写交回原生成 agent，避免「审核者即改写者」冲突。故 reviewer 必须是独立 agent，
不挂在 guide/photo 等生成 agent 上。

失败哲学：任何环节失败返回 None，调用方降级到规则版（关键词红线扫描），
保证 `/review/content` 永不因 agent 抖动而 500。对齐 route/intent agent 纪律。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError

logger = logging.getLogger("macau_storywalk.reviewer_agent")

# QwenPaw 中独立审核 agent 的 id（需手动在 Console 建，见 skills/README.md）
REVIEWER_AGENT_ID = "reviewer"

_VALID_DECISIONS = {"pass", "revise", "block"}
_VALID_SEVERITY = {"high", "medium", "low"}


class ReviewIssue(BaseModel):
    dimension: str = ""
    severity: str = "low"   # high | medium | low
    detail: str = ""
    fix: str = ""


class ReviewVerdict(BaseModel):
    """reviewer agent 输出的结构化裁定。"""
    decision: str = "pass"   # pass | revise | block
    issues: list[ReviewIssue] = Field(default_factory=list)
    reviewer_notes: str = ""


def _build_prompt(text: str, source_type: str | None = None) -> str:
    """构造发给 reviewer agent 的 prompt（agent 自带 content-safety-review 技能为 system prompt）。"""
    src = f"\n内容来源标注：{source_type}" if source_type else ""
    return (
        "待审核内容：" + text.strip() + src + "\n\n"
        "请按 content-safety-review 技能输出严格 JSON（首字符为 {，无解释、无代码围栏）。"
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 agent 文本里抽首个 {...} 并解析；失败返回 None。"""
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


def _coerce(obj: dict[str, Any]) -> ReviewVerdict:
    """把 agent 的 JSON 清洗成 ReviewVerdict（容忍命名差异，丢未知值）。"""
    decision = obj.get("decision")
    if not isinstance(decision, str) or decision not in _VALID_DECISIONS:
        decision = "pass"

    issues: list[ReviewIssue] = []
    for raw in obj.get("issues") or []:
        if not isinstance(raw, dict):
            continue
        sev = raw.get("severity")
        if not isinstance(sev, str) or sev not in _VALID_SEVERITY:
            sev = "low"
        issues.append(ReviewIssue(
            dimension=str(raw.get("dimension", ""))[:40],
            severity=sev,
            detail=str(raw.get("detail", ""))[:300],
            fix=str(raw.get("fix", ""))[:300],
        ))

    return ReviewVerdict(
        decision=decision,
        issues=issues,
        reviewer_notes=str(obj.get("reviewer_notes", ""))[:300],
    )


def parse_review(
    text: str,
    *,
    source_type: str | None = None,
    client: QwenPawClient | None = None,
) -> ReviewVerdict | None:
    """调 reviewer agent 审核内容。任一环节失败返回 None（→ 调用方降级规则版）。"""
    client = client or QwenPawClient()
    try:
        reply = client.ask(
            REVIEWER_AGENT_ID, _build_prompt(text, source_type), session_name="harness-reviewer"
        )
    except QwenPawError as exc:
        logger.info("reviewer agent 调用失败，降级规则版：%s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 网络/传输层任何意外都不抛穿，降级规则版
        logger.info("reviewer agent 调用异常，降级规则版：%s", exc)
        return None

    obj = _extract_json(reply)
    if obj is None:
        logger.info("reviewer agent 输出非 JSON，降级规则版。原文：%s", (reply or "")[:200])
        return None

    try:
        return _coerce(obj)
    except (ValidationError, TypeError) as exc:
        logger.info("reviewer agent 输出校验失败，降级规则版：%s", exc)
        return None
