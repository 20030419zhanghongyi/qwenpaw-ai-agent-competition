from fastapi import APIRouter, HTTPException

from .adjuster import RouteAdjustRequest, adjust_route
from app.models.user import Preference

from .matcher import match_routes
from .repository import get_template, list_templates

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.get("")
def list_routes() -> list[dict]:
    """全部预设路线模板。"""
    return list_templates()


@router.post("/match")
def match(pref: Preference) -> dict:
    """根据偏好返回最匹配的路线结果（无 API key 第一阶段）。

    当前链路：
    - 模板路线召回
    - 候选 POI 召回
    - 约束式排线

    未来 Phase 3 再接 /routes/adjust 做 Agent 微调。
    """
    matches = match_routes(pref)
    return {"preference": pref.model_dump(), "matches": matches}


@router.post("/adjust")
def adjust(request: RouteAdjustRequest) -> dict:
    """无 API key 的规则版路线微调接口。

    当前只支持少量高频自然语言偏好：
    - 不想太累 / 少走路
    - 不要回头路
    - 想拍照 / 加个拍照点
    - 想吃点东西
    """
    try:
        return adjust_route(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{route_id}")
def get_route_detail(route_id: str) -> dict:
    route = get_template(route_id)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route not found: {route_id}")
    return route
