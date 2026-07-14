"""Orchestrator 意图分类与 Agent 路由测试。"""

from fastapi.testclient import TestClient

from app.main import app
from app.orchestrator.router import RouteRequest, classify_intent

client = TestClient(app)


def test_initial_trip_requirement_routes_to_intent_agent():
    decision = classify_intent(RouteRequest(text="下午带老人少走路，想看建筑"))

    assert decision.intent == "trip_requirement"
    assert decision.agent_id == "intent"
    assert decision.agent_chain == ["intent"]


def test_existing_route_adjustment_routes_to_route_agent():
    decision = classify_intent(
        RouteRequest(text="把最后一站删掉，路线少走一点", current_route_id="heritage_fullday")
    )

    assert decision.intent == "route_adjustment"
    assert decision.agent_id == "route"
    assert "current_route_id" in decision.signals


def test_poi_question_routes_to_guide_agent():
    decision = classify_intent(RouteRequest(text="妈阁庙为什么和澳门的名字有关？"))

    assert decision.intent == "poi_guide"
    assert decision.agent_id == "guide"


def test_current_route_context_does_not_turn_guide_question_into_adjustment():
    decision = classify_intent(
        RouteRequest(text="讲讲最后一站有什么历史", current_route_id="heritage_fullday")
    )

    assert decision.intent == "poi_guide"
    assert decision.agent_id == "guide"


def test_uploaded_photo_can_chain_recognition_then_guide():
    decision = classify_intent(RouteRequest(text="这是什么建筑？再讲讲它的历史", has_image=True))

    assert decision.intent == "photo_recognition"
    assert decision.agent_id == "photo"
    assert decision.agent_chain == ["photo", "guide"]


def test_explicit_content_audit_has_priority_over_image():
    decision = classify_intent(
        RouteRequest(text="审核这张宣传图有没有隐私或安全风险", has_image=True)
    )

    assert decision.intent == "content_review"
    assert decision.agent_id == "reviewer"


def test_ambiguous_input_falls_back_to_intent_agent_with_low_confidence():
    decision = classify_intent(RouteRequest(text="帮帮我"))

    assert decision.agent_id == "intent"
    assert decision.fallback is True
    assert decision.confidence <= 0.4


def test_orchestrator_route_api_returns_explainable_decision():
    response = client.post(
        "/api/v1/orchestrator/route",
        json={"text": "这条路线太累了，帮我换一站", "current_route_id": "culture_halfday"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "route"
    assert data["intent"] == "route_adjustment"
    assert data["reason"]
    assert data["confidence"] >= 0.8
