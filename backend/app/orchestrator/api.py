"""Orchestrator HTTP 接口。"""

from fastapi import APIRouter

from app.observability.trace import record_trace
from app.orchestrator.router import RouteDecision, RouteRequest, classify_intent

router = APIRouter(prefix="/api/v1/orchestrator", tags=["orchestrator"])


@router.post("/route", response_model=RouteDecision)
def route(request: RouteRequest) -> RouteDecision:
    """分类用户意图并返回目标 Agent；本接口不直接触发 LLM 调用。"""
    decision = classify_intent(request)
    record_trace(
        kind="orchestrator.route",
        status="fallback" if decision.fallback else "ok",
        agent_id=decision.agent_id,
        input_summary=request.text[:200],
        extra={
            "intent": decision.intent.value,
            "agent_chain": decision.agent_chain,
            "confidence": decision.confidence,
        },
    )
    return decision
