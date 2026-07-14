"""用户意图分类与 QwenPaw Agent 路由。

路由层只回答“该交给谁”，不直接执行业务 Agent。规则保持保守、可解释：
有已选路线的修改请求交给 ``route``；首次出行需求交给 ``intent``；景点问答交给
``guide``；带图识别交给 ``photo``；显式内容审核交给 ``reviewer``。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class UserIntent(str, Enum):
    """外层 harness 支持的业务意图。"""

    TRIP_REQUIREMENT = "trip_requirement"
    ROUTE_ADJUSTMENT = "route_adjustment"
    POI_GUIDE = "poi_guide"
    PHOTO_RECOGNITION = "photo_recognition"
    CONTENT_REVIEW = "content_review"


class RouteRequest(BaseModel):
    """意图路由输入；上下文字段用于消除“首次规划/已有路线修改”歧义。"""

    text: str = ""
    has_image: bool = False
    current_route_id: str | None = None


class RouteDecision(BaseModel):
    """可审计的路由决定。``agent_chain`` 支持识图后继续讲解。"""

    intent: UserIntent
    agent_id: str
    agent_chain: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    signals: list[str] = Field(default_factory=list)
    fallback: bool = False


_REVIEW_CUES = (
    "审核",
    "审查",
    "合规",
    "安全风险",
    "隐私风险",
    "敏感信息",
    "是否违规",
    "能不能发布",
)
_IMAGE_REFERENCES = ("图片", "照片", "相片", "画面", "这张图", "这是什么建筑")
_IMAGE_ACTIONS = ("识别", "认一下", "这是哪里", "是什么地方", "拍的是", "这是什么")
_ROUTE_OBJECTS = ("路线", "行程", "最后一站", "上一站", "下一站", "景点顺序")
_ROUTE_ACTIONS = (
    "调整",
    "修改",
    "换一站",
    "换个",
    "删掉",
    "去掉",
    "加一站",
    "少走",
    "别绕",
    "顺路",
    "不要回头",
    "太累",
    "累了",
    "不想太累",
)
_GUIDE_CUES = (
    "讲讲",
    "介绍",
    "有什么故事",
    "有什么历史",
    "为什么",
    "是什么来历",
    "建筑特色",
    "文化背景",
)
_TRIP_CUES = (
    "想去",
    "想看",
    "想吃",
    "想玩",
    "帮我规划",
    "帮我安排",
    "半天",
    "全天",
    "下午",
    "上午",
    "晚上",
    "夜游",
    "带老人",
    "带小孩",
    "亲子",
    "一个人",
    "朋友",
    "少走",
    "美食",
    "拍照",
    "建筑",
)


def _matches(text: str, cues: tuple[str, ...]) -> list[str]:
    return [cue for cue in cues if cue in text]


def _decision(
    intent: UserIntent,
    agent_id: str,
    confidence: float,
    reason: str,
    signals: list[str],
    *,
    agent_chain: list[str] | None = None,
    fallback: bool = False,
) -> RouteDecision:
    return RouteDecision(
        intent=intent,
        agent_id=agent_id,
        agent_chain=agent_chain or [agent_id],
        confidence=confidence,
        reason=reason,
        signals=list(dict.fromkeys(signals)),
        fallback=fallback,
    )


def classify_intent(request: RouteRequest) -> RouteDecision:
    """按显式上下文和保守优先级分类，返回目标 Agent 与可解释证据。"""
    text = (request.text or "").strip()

    review_hits = _matches(text, _REVIEW_CUES)
    if review_hits:
        return _decision(
            UserIntent.CONTENT_REVIEW,
            "reviewer",
            0.96,
            "用户显式要求审核内容，先进入独立安全审核 Agent。",
            review_hits,
        )

    guide_hits = _matches(text, _GUIDE_CUES)
    image_hits = _matches(text, _IMAGE_REFERENCES) + _matches(text, _IMAGE_ACTIONS)
    if request.has_image or (
        _matches(text, _IMAGE_REFERENCES) and _matches(text, _IMAGE_ACTIONS)
    ):
        chain = ["photo", "guide"] if guide_hits else ["photo"]
        signals = (["has_image"] if request.has_image else []) + image_hits + guide_hits
        reason = "请求包含待识别图片，先交给多模态识图 Agent。"
        if len(chain) > 1:
            reason += "识别后继续交给文化讲解 Agent。"
        return _decision(
            UserIntent.PHOTO_RECOGNITION,
            "photo",
            0.98 if request.has_image else 0.9,
            reason,
            signals,
            agent_chain=chain,
        )

    route_object_hits = _matches(text, _ROUTE_OBJECTS)
    route_action_hits = _matches(text, _ROUTE_ACTIONS)
    route_hits = route_object_hits + route_action_hits
    has_route_adjustment = bool(route_action_hits) and bool(
        request.current_route_id or route_object_hits
    )
    if has_route_adjustment:
        signals = (["current_route_id"] if request.current_route_id else []) + route_hits
        return _decision(
            UserIntent.ROUTE_ADJUSTMENT,
            "route",
            0.95 if request.current_route_id else 0.86,
            "请求针对已有路线或行程节点做增量修改，交给路线微调 Agent。",
            signals,
        )

    if guide_hits:
        return _decision(
            UserIntent.POI_GUIDE,
            "guide",
            0.88,
            "请求询问景点的历史、故事或文化背景，交给文化讲解 Agent。",
            guide_hits,
        )

    trip_hits = _matches(text, _TRIP_CUES)
    if trip_hits:
        return _decision(
            UserIntent.TRIP_REQUIREMENT,
            "intent",
            0.82,
            "请求描述首次出行偏好，交给需求理解 Agent 生成结构化 Preference。",
            trip_hits,
        )

    return _decision(
        UserIntent.TRIP_REQUIREMENT,
        "intent",
        0.32,
        "未发现足够明确的业务信号，保守回落到需求理解 Agent 继续澄清。",
        [],
        fallback=True,
    )
