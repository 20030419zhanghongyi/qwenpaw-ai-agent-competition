"""内容审核接口（QwenPaw reviewer agent 驱动，规则版作 fallback）。

- ``REVIEWER_AGENT_ENABLED=true`` 且 reviewer agent 可用时：调 agent 做合规与安全审核
  （source="agent"）
- 否则降级规则版关键词红线扫描（source="rules"），保证接口永不被 agent 抖动打穿

设计：审核是「内容 → 裁定」的独立 pipe，输入待审核文本，输出 {decision, issues,
reviewer_notes, source}。生成方（guide/photo）的输出可串到此端点做上线前把关。
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.agents import reviewer_agent
from app.core.config import settings
from app.guardrails.runtime import rate_limit, sanitize_untrusted_text
from app.observability.trace import record_trace

logger = logging.getLogger("macau_storywalk.review")

router = APIRouter(prefix="/api/v1/review", tags=["review"])


class ReviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    source_type: str | None = None   # official / academic / folklore / ai，可选提示

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        value = sanitize_untrusted_text(value)
        if not value:
            raise ValueError("text must not be blank")
        return value


# --- 规则版 fallback：关键词红线扫描（保守，只认明确红线，语义判断留给 agent）---

# block 级：紧急救援 / 权威导航 / 索要敏感个人信息
_BLOCK_KEYWORDS = (
    "紧急", "救护", "报警", "急救", "叫120", "120", "999",
    "身份证", "护照号", "银行卡", "卡号", "密码", "社保号",
)
# revise 级：把不确定内容表述为确定（编造/逢迎风险信号）
_OVERCONFIDENT_RE = re.compile(r"(制于|建于|成于|造于)\s*\d{4}\s*年|一定(是|来自)|肯定是|绝对是|毫无疑问")
# revise 级：对历史属性下无来源的强断言
_UNSOURCED_RE = re.compile(r"(以前|曾经|原本)是(皇宫|官府|衙门|行宫)")


def parse_review_rules(text: str, source_type: str | None = None) -> dict:
    """规则版审核：扫红线关键词 + 过度自信断言。返回与 agent 同形的裁定 dict。"""
    t = text or ""
    issues: list[dict] = []

    hit_block = [k for k in _BLOCK_KEYWORDS if k in t]
    if hit_block:
        issues.append({
            "dimension": "越界/安全",
            "severity": "high",
            "detail": f"命中红线词：{', '.join(hit_block)}",
            "fix": "删除紧急救援/权威导航结论，或敏感信息索要",
        })
        decision = "block"
    elif _OVERCONFIDENT_RE.search(t) or _UNSOURCED_RE.search(t):
        issues.append({
            "dimension": "事实准确性",
            "severity": "medium",
            "detail": "疑似把不确定内容表述为确定事实（过度自信/无来源）",
            "fix": "降置信或加来源，必要时改为「未能确定」",
        })
        decision = "revise"
    else:
        decision = "pass"

    return {
        "decision": decision,
        "issues": issues,
        "reviewer_notes": "规则版关键词红线扫描（agent 不可用时的 baseline）",
    }


def review_text(text: str, source_type: str | None = None) -> dict:
    """核心审核逻辑（agent 先行，失败降级规则版）——端点与 guide→reviewer 管道共用。

    返回带 ``source``（"agent"|"rules"）的裁定 dict：
    ``{decision, issues, reviewer_notes, source}``。reviewer agent 不可用 / 解析失败
    时自动回落规则版（``source="rules"``），永不抛穿。
    """
    source = "rules"
    verdict = parse_review_rules(text, source_type)

    if settings.reviewer_agent_enabled:
        agent_verdict = reviewer_agent.parse_review(text, source_type=source_type)
        if agent_verdict is not None:
            verdict = agent_verdict.model_dump()
            source = "agent"
        else:
            logger.info("reviewer agent 不可用或解析失败，降级规则版")

    verdict["source"] = source
    return verdict


@router.post("/content", dependencies=[Depends(rate_limit("text"))])
def review(request: ReviewRequest) -> dict:
    """待上线内容 → 审核裁定（agent 先行，失败降级规则版）。"""
    verdict = review_text(request.text, request.source_type)
    record_trace(
        kind="review.content",
        status=verdict["source"],
        agent_id="reviewer" if verdict["source"] == "agent" else None,
        input_summary=request.text[:200],
        extra={"decision": verdict.get("decision"), "source_type": request.source_type},
    )
    return verdict
