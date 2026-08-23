"""Long-term preference memory and multi-agent workflow contracts."""

from app.features.users.repository import _empty_memory, _record_preference
from app.models.user import Preference
from app.orchestrator.router import RouteRequest, classify_intent


def test_preference_memory_accumulates_only_structured_signals():
    memory = _record_preference(
        _empty_memory(),
        Preference(
            duration="full-day",
            themes=["heritage"],
            interests=["history", "architecture"],
            physical=["less-walk"],
            language="zh-CN",
            travel_date="2026-10-03",
        ),
    )

    assert memory["preference_updates"] == 1
    assert memory["signal_counts"]["themes"] == {"heritage": 1}
    assert memory["signal_counts"]["physical"] == {"less-walk": 1}
    assert "travel_date" not in memory["latest_preference"]


def test_orchestrator_returns_ordered_workflow_and_memory_context():
    decision = classify_intent(
        RouteRequest(
            text="请识别这张图片并讲讲它的历史",
            has_image=True,
            user_id="user-42",
            current_route_id="heritage_halfday",
        )
    )

    assert decision.agent_chain == ["photo", "guide"]
    assert [step.agent_id for step in decision.workflow] == ["photo", "guide"]
    assert decision.workflow[1].depends_on == ["step_1"]
    assert decision.shared_context["memory_key"] == "user:user-42:preference-memory"
    assert decision.shared_context["route_id"] == "heritage_halfday"
