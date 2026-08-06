"""Guide Agent Console sessions must not mix unrelated conversations."""

from app.agents import guide_agent


class _Client:
    def __init__(self) -> None:
        self.session_names: list[str] = []

    def ask(self, agent_id: str, prompt: str, *, session_name: str) -> str:
        assert agent_id == "guide"
        assert prompt
        self.session_names.append(session_name)
        return (
            '{"text":"讲解","source_type":"official","confidence":0.9,'
            '"ai_generated":true,"language":"zh-CN"}'
        )


def test_generate_uses_a_unique_console_session_per_request() -> None:
    client = _Client()

    assert guide_agent.generate("议事亭前地", material="可靠资料", client=client) is not None
    assert guide_agent.generate("大三巴牌坊", material="可靠资料", client=client) is not None

    assert len(client.session_names) == 2
    assert client.session_names[0] != client.session_names[1]
    assert all(name.startswith("harness-guide-") for name in client.session_names)


def test_answer_uses_a_unique_console_session_per_request() -> None:
    client = _Client()

    assert guide_agent.answer("议事亭前地", "有什么故事？", material="可靠资料", client=client)
    assert guide_agent.answer("大三巴牌坊", "有什么特色？", material="可靠资料", client=client)

    assert len(client.session_names) == 2
    assert client.session_names[0] != client.session_names[1]
    assert all(name.startswith("harness-guide-ask-") for name in client.session_names)
