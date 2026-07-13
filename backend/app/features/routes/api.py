import logging

from fastapi import APIRouter, HTTPException

from app.agents import route_agent
from app.api.contracts import NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.core.config import settings
from app.models.user import Preference
from app.observability.trace import record_trace

from .adjuster import RouteAdjustRequest, adjust_route
from .models import RouteAdjustResponse, RouteMatchResponse, RouteTemplateResponse
from .service import route_service

logger = logging.getLogger("macau_storywalk.routes")

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.get(
    "",
    response_model=list[RouteTemplateResponse],
    summary="List route templates",
    description="Return database-backed route templates in their configured order.",
)
def list_routes() -> list[dict]:
    """全部预设路线模板。"""
    return route_service.list_templates()


@router.post(
    "/match",
    response_model=RouteMatchResponse,
    summary="Match route templates",
    description="Rank persisted route templates for the supplied travel preferences.",
    responses=UNPROCESSABLE_RESPONSE,
)
def match(pref: Preference) -> dict:
    """根据偏好返回最匹配的路线结果（无 API key 第一阶段）。

    当前链路：
    - 模板路线召回
    - 候选 POI 召回
    - 约束式排线

    未来 Phase 3 再接 /routes/adjust 做 Agent 微调。
    """
    matches = route_service.match(pref)
    return {"preference": pref.model_dump(), "matches": matches}


@router.post(
    "/adjust",
    response_model=RouteAdjustResponse,
    summary="Adjust a route",
    description="Apply the existing route-adjustment behavior to a persisted template.",
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def adjust(request: RouteAdjustRequest) -> dict:
    """路线微调接口（P1：QwenPaw 路线 agent 驱动，规则版作 fallback）。

    - ``ROUTE_AGENT_ENABLED=true`` 且 route agent 可用时：先调 agent 把自然语言翻成
      结构化意图 → 叠加到 Preference → 喂给现成排线引擎（source="agent"）
    - 否则降级规则版关键词解析（source="rules"），保证接口永不被 agent 抖动打穿
    """
    pref_override = None
    source = "rules"

    if settings.route_agent_enabled:
        adjustment = route_agent.parse_route_adjustment(
            request.instruction, request.preference, request.route_id
        )
        if adjustment is not None:
            pref_override = route_agent.apply_adjustment_to_preference(request.preference, adjustment)
            source = "agent"
        else:
            logger.info("route agent 不可用或解析失败，降级规则版")

    try:
        result = adjust_route(request, preference_override=pref_override)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result["source"] = source
    record_trace(
        kind="routes.adjust",
        status=source,
        agent_id="route" if source == "agent" else None,
        input_summary=request.instruction[:200],
        extra={"route_id": request.route_id},
    )
    return result


@router.get(
    "/{route_id}",
    response_model=RouteTemplateResponse,
    summary="Get a route template",
    responses=NOT_FOUND_RESPONSE,
)
def get_route_detail(route_id: str) -> dict:
    route = route_service.get_template(route_id)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route not found: {route_id}")
    return route
