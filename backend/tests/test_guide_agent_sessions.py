"""Guide Agent Console sessions must not mix unrelated conversations."""

from app.agents import guide_agent
from app.agents.qwenpaw_client import QwenPawError


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


def test_translate_search_queries_returns_all_retrieval_languages() -> None:
    prompts: list[str] = []

    class TranslationClient:
        def ask(self, agent_id, prompt, *, session_name, max_duration=None):
            assert agent_id == "guide"
            assert session_name.startswith("guide-query-translate-")
            assert max_duration == guide_agent.settings.guide_query_translation_max_duration
            prompts.append(prompt)
            return (
                '{"zh-CN":"什么时候建成","en":"when was it completed",'
                '"pt":"quando foi concluído"}'
            )

    translated = guide_agent.translate_search_queries(
        "这是什么时候建立的？",
        input_language="zh-CN",
        client=TranslationClient(),
    )

    assert translated == {
        "zh-CN": "什么时候建成",
        "en": "when was it completed",
        "pt": "quando foi concluído",
    }
    assert "Do not answer" in prompts[0]
    assert "Detected input language: zh-CN" in prompts[0]


def test_answer_prompt_separates_input_and_profile_languages() -> None:
    prompts: list[str] = []

    class AnswerClient:
        def ask(self, _agent_id, prompt, *, session_name):
            prompts.append(prompt)
            return (
                '{"text":"It opened in 2018.","source_type":"official",'
                '"confidence":0.9,"ai_generated":true,"language":"en"}'
            )

    result = guide_agent.answer(
        "Hong Kong-Zhuhai-Macao Bridge Macao Port",
        "这是什么时候建立的？",
        material="Official source: opened in 2018.",
        language="en",
        input_language="zh-CN",
        client=AnswerClient(),
    )

    assert result is not None
    assert "检测到的提问语言：zh-CN" in prompts[0]
    assert "个人中心设定的回答语言：en" in prompts[0]
    assert "Answer only in natural, concise English" in prompts[0]


def _reset_guide_runtime_state() -> None:
    with guide_agent._state_lock:
        guide_agent._cache.clear()
        guide_agent._failure_until = 0.0


def test_generate_caches_successful_enhancement(monkeypatch) -> None:
    _reset_guide_runtime_state()
    calls: list[float | None] = []

    class ManagedClient:
        def __init__(self, **_kwargs) -> None:
            pass

        def ask(self, _agent_id, _prompt, *, session_name, max_duration=None):
            assert session_name.startswith("harness-guide-")
            calls.append(max_duration)
            return (
                '{"text":"Guide","source_type":"official","confidence":0.9,'
                '"ai_generated":true,"language":"en"}'
            )

    monkeypatch.setattr(guide_agent, "QwenPawClient", ManagedClient)

    first = guide_agent.generate("POI", material="source", language="en")
    second = guide_agent.generate("POI", material="source", language="en")

    assert first is not None and second is not None
    assert calls == [guide_agent.settings.guide_agent_max_duration]


def test_generate_opens_short_circuit_after_failure(monkeypatch) -> None:
    _reset_guide_runtime_state()
    calls = 0

    class FailingClient:
        def __init__(self, **_kwargs) -> None:
            pass

        def ask(self, *_args, **_kwargs):
            nonlocal calls
            calls += 1
            raise QwenPawError("slow model")

    monkeypatch.setattr(guide_agent, "QwenPawClient", FailingClient)

    assert guide_agent.generate("POI", material="source", language="en") is None
    assert guide_agent.generate("POI", material="source", language="en") is None
    assert calls == 1
