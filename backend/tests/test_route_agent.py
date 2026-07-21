"""Route and intent agent normalization tests without QwenPaw network calls."""

from app.agents import intent_agent, route_agent
from app.models.user import Preference


class StubClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict] = []

    def ask(self, agent_id: str, text: str, **kwargs) -> str:
        self.calls.append({"agent_id": agent_id, "text": text, **kwargs})
        return self.reply


def test_route_action_fields_are_applied_to_preference():
    adjustment = route_agent.RouteAdjustment(
        add_nodes=["food"],
        remove_tail=True,
        reorder_by_district=True,
    )

    updated = route_agent.apply_adjustment_to_preference(
        Preference(interests=["culture"]),
        adjustment,
    )

    assert updated.interests == ["culture", "food"]
    assert updated.physical == ["less-walk", "no-backtrack"]


def test_route_adjustment_requires_an_executable_action():
    assert route_agent.is_actionable(
        route_agent.RouteAdjustment(notes="未识别到可执行的偏好调整")
    ) is False
    assert route_agent.is_actionable(
        route_agent.RouteAdjustment(add_nodes=["photo"])
    ) is True


def test_route_agent_uses_a_fresh_session_for_each_parse():
    client = StubClient(
        '{"preference_add":{"interests":["food"]},"add_nodes":["food"]}'
    )
    preference = Preference(interests=["culture"])

    first = route_agent.parse_route_adjustment(
        "加一个美食点",
        preference,
        "culture_halfday",
        client=client,
    )
    second = route_agent.parse_route_adjustment(
        "再加一个美食点",
        preference,
        "culture_halfday",
        client=client,
    )

    assert first is not None and second is not None
    assert client.calls[0]["session_id"] != client.calls[1]["session_id"]


def test_intent_agent_uses_a_fresh_session_for_each_parse():
    client = StubClient(
        '{"duration":"half-day","party_size":1,"travel_type":["solo"],'
        '"interests":["food"],"physical":[],"language":"zh-CN"}'
    )

    first = intent_agent.parse_intent("一个人去吃东西", client=client)
    second = intent_agent.parse_intent("一个人再去吃东西", client=client)

    assert first is not None and second is not None
    assert client.calls[0]["session_id"] != client.calls[1]["session_id"]
