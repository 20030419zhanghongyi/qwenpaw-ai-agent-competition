"""Guide /ask：web-first（本地 KB 偏稀）；短超时联网为主，本地仅兜底。"""

from __future__ import annotations

import re
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.features.guide import api as guide_api
from app.features.intent import api as intent_api
from app.guardrails.runtime import rate_limiter
from app.main import app
from app.observability import trace

client = TestClient(app)

_DASHABA_MATERIAL = (
    "intro: 大三巴牌坊是澳门最具标志性的历史遗迹，原为圣保禄大教堂的前壁，"
    "属『澳门历史城区』世界遗产核心景点。\n"
    "history: 原为圣保禄大教堂，17世纪初由耶稣会士建造，曾是远东最大的天主教堂之一。"
    "1835年毁于大火，仅存石砌前壁与阶梯。"
)


def _reset(monkeypatch, tmp_path):
    rate_limiter.clear()
    monkeypatch.setattr(intent_api, "record_trace", lambda **_: None)
    monkeypatch.setattr(guide_api, "record_trace", lambda **_: None)
    monkeypatch.setattr(trace, "_trace_path", lambda: tmp_path / "trace.jsonl")
    monkeypatch.setattr(
        guide_api,
        "_apply_review",
        lambda text, *, path: (text, {"decision": "pass", "source": "skipped"}),
    )
    monkeypatch.setattr(guide_api.settings, "guide_agent_enabled", False)
    monkeypatch.setattr(
        guide_api.guide_agent,
        "translate_search_queries",
        lambda *_a, **_k: {},
    )


def _stub_local(monkeypatch, name: str, material: str):
    monkeypatch.setattr(
        guide_api,
        "_gather_material_fast",
        lambda *_a, **_k: (name, material),
    )


def test_ask_calls_web_even_when_local_is_strong(monkeypatch, tmp_path):
    """Web-first：本地强命中仍应联网；有 web 命中时以 web 为主。"""
    _reset(monkeypatch, tmp_path)
    _stub_local(monkeypatch, "大三巴牌坊", _DASHABA_MATERIAL)
    called: dict = {"n": 0, "queries": None}

    def _fake_search(queries, **_kw):
        called["n"] += 1
        called["queries"] = list(queries)
        return [
            {
                "title": "Ruins of St. Paul's",
                "snippet": "The Ruins of St. Paul's are the remains of a 17th-century complex.",
                "url": "https://example.com/stpaul",
                "source": "wikipedia:en",
            }
        ]

    monkeypatch.setattr(guide_api, "search_web_multi", _fake_search)
    agent_calls: list = []
    monkeypatch.setattr(
        guide_api.guide_agent,
        "answer",
        lambda *_a, **_k: agent_calls.append(1) or None,
    )

    answer, weak = guide_api._material_snippet_answer(
        "这个建筑原来是干什么的",
        _DASHABA_MATERIAL,
        language="zh-CN",
    )
    assert weak is False
    assert "圣保禄" in answer

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "大三巴牌坊",
            "question": "这个建筑原来是干什么的",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert called["n"] == 3
    assert payload["web_used"] is True
    assert payload["source"] == "web"
    assert "St. Paul" in payload["text"] or "17th-century" in payload["text"]
    assert agent_calls == []  # 默认不调 agent
    assert "手头资料里没有" not in payload["text"]


def test_local_fallback_when_web_empty(monkeypatch, tmp_path):
    """联网无结果时回落本地「原为…」摘录。"""
    _reset(monkeypatch, tmp_path)
    _stub_local(monkeypatch, "大三巴牌坊", _DASHABA_MATERIAL)
    monkeypatch.setattr(guide_api, "search_web_multi", lambda *_a, **_k: [])

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "大三巴牌坊",
            "question": "这个建筑原来是干什么的",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is False
    assert payload["source"] == "rules"
    assert "圣保禄" in payload["text"]
    assert "手头资料里没有" not in payload["text"]


def test_web_false_uses_local_only(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    _stub_local(monkeypatch, "大三巴牌坊", _DASHABA_MATERIAL)
    called = {"n": 0}

    def _boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("web=false must not call search")

    monkeypatch.setattr(guide_api, "search_web_multi", _boom)

    response = client.post(
        "/api/v1/guide/ask?web=false",
        json={
            "poi": "大三巴牌坊",
            "question": "这个建筑原来是干什么的",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert called["n"] == 0
    assert payload["web_used"] is False
    assert "圣保禄" in payload["text"]


def test_weak_local_served_from_web_snippets(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    _stub_local(monkeypatch, "议事亭前地", "intro: 这是澳门市中心的广场。")
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_a, **_k: [
            {
                "title": "Largo do Senado",
                "snippet": "Senado Square was the seat of Macau's municipal council.",
                "url": "https://example.com/senado",
                "source": "wikipedia:en",
            }
        ],
    )

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "议事亭前地",
            "question": "附近地铁站叫什么名字啊到底",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is True
    assert payload["source"] == "web"
    assert "municipal council" in payload["text"] or "Senado" in payload["text"]
    assert payload["web_sources"]
    assert "手头资料里没有" not in payload["text"]


def test_empty_only_when_local_and_web_both_fail(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    _stub_local(monkeypatch, "某地标", "intro: 一座普通建筑。")
    monkeypatch.setattr(guide_api, "search_web_multi", lambda *_a, **_k: [])

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "某地标",
            "question": "量子纠缠门票多少钱",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is False
    assert "暂未" in payload["text"]
    assert "检索到可靠的相关资料" in payload["text"]
    assert "没有答案" not in payload["text"]
    assert "手头资料里没有" not in payload["text"]


def test_agent_only_when_enhance_true(monkeypatch, tmp_path):
    """默认不调 agent；enhance=true 才用 agent 综合 web。"""
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(guide_api.settings, "guide_agent_enabled", True)
    _stub_local(monkeypatch, "大三巴牌坊", "intro: 石砌前壁遗迹。")
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_a, **_k: [
            {
                "title": "Ruins of St. Paul's",
                "snippet": "The façade is the remains of the Church of Mater Dei.",
                "url": "https://example.com/stpaul",
                "source": "wikipedia:en",
            }
        ],
    )

    class _Expl:
        text = "这是圣保禄教堂前壁遗迹，原属 Mater Dei。"
        confidence = 0.85
        source_type = "ai"
        ai_generated = True
        language = "zh-CN"

    calls: list = []

    def _answer(*_a, **_k):
        calls.append(1)
        return _Expl()

    monkeypatch.setattr(guide_api.guide_agent, "answer", _answer)

    # default: no agent
    r1 = client.post(
        "/api/v1/guide/ask",
        json={"poi": "大三巴牌坊", "question": "教堂原来供奉哪位圣人", "language": "zh-CN"},
    )
    assert r1.status_code == 200
    assert r1.json()["source"] == "web"
    assert calls == []

    # enhance: agent
    r2 = client.post(
        "/api/v1/guide/ask?enhance=true",
        json={"poi": "大三巴牌坊", "question": "教堂原来供奉哪位圣人", "language": "zh-CN"},
    )
    assert r2.status_code == 200
    assert r2.json()["source"] == "agent+web"
    assert "Mater Dei" in r2.json()["text"] or "圣保禄" in r2.json()["text"]
    assert len(calls) == 1


def test_agent_refusal_prefers_web_snippets(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(guide_api.settings, "guide_agent_enabled", True)
    _stub_local(monkeypatch, "大三巴牌坊", "intro: 石砌前壁遗迹。")
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_a, **_k: [
            {
                "title": "Ruins of St. Paul's",
                "snippet": "The façade is the remains of the Church of Mater Dei.",
                "url": "https://example.com/stpaul",
                "source": "wikipedia:en",
            }
        ],
    )

    class _Expl:
        text = "手头资料里没有直接答案。你可以换个问法。"
        confidence = 0.2
        source_type = "ai"
        ai_generated = True
        language = "zh-CN"

    monkeypatch.setattr(guide_api.guide_agent, "answer", lambda *_a, **_k: _Expl())

    response = client.post(
        "/api/v1/guide/ask?enhance=true",
        json={
            "poi": "大三巴牌坊",
            "question": "教堂原来供奉哪位圣人",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is True
    assert payload["source"] == "web"
    assert "Church of Mater Dei" in payload["text"] or "façade" in payload["text"]
    assert "手头资料里没有" not in payload["text"]


def test_web_only_poi_without_local_material(monkeypatch, tmp_path):
    """本地完全无料时仍可 web-first 作答，不 404。"""
    _reset(monkeypatch, tmp_path)
    _stub_local(monkeypatch, "", "")
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_a, **_k: [
            {
                "title": "Macau Tower",
                "snippet": "Macau Tower is a tower in Sé, Macau.",
                "url": "https://example.com/tower",
                "source": "wikipedia:en",
            }
        ],
    )

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "Macau Tower",
            "question": "这是什么建筑",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is True
    assert payload["source"] == "web"
    assert "Macau Tower" in payload["text"] or "tower" in payload["text"].lower()


def test_english_ask_localizes_chinese_poi_key(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    seen_queries: list[str] = []

    def _search(queries, **_kwargs):
        seen_queries.extend(queries)
        return [
            {
                "title": "Ruins of Saint Paul's",
                "snippet": "The church complex was largely destroyed by fire in 1835.",
                "url": "https://example.com/stpaul",
                "source": "wikipedia:en",
            }
        ]

    monkeypatch.setattr(guide_api, "search_web_multi", _search)
    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "大三巴牌坊",
            "question": "How has it changed over time?",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["poi_name"] == "Ruins of St. Paul's"
    assert "About Ruins of St. Paul's" in payload["text"]
    assert re.search(r"[\u3400-\u9fff]", payload["text"]) is None
    assert "（" not in payload["text"]
    assert any("Ruins of St. Paul's" in query for query in seen_queries)


def test_portuguese_ask_filters_chinese_web_snippet(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_args, **_kwargs: [
            {
                "title": "大三巴牌坊",
                "snippet": "大三巴牌坊在1835年的火灾后只留下前壁。",
                "url": "https://example.com/zh",
                "source": "web",
            }
        ],
    )

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "大三巴牌坊",
            "question": "Como mudou ao longo do tempo?",
            "language": "pt",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["poi_name"] == "Ruínas de S. Paulo"
    assert re.search(r"[\u3400-\u9fff]", payload["text"]) is None


def test_macao_museum_rejects_unrelated_museum_results(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_args, **_kwargs: [
            {
                "title": "Hong Kong",
                "snippet": "Hong Kong is a special administrative region of China.",
                "url": "https://example.com/hong-kong",
                "source": "wikipedia:en",
            },
            {
                "title": "Macao Museum",
                "snippet": "Macao Museum presents the history and cultures of Macau.",
                "url": "https://example.com/macao-museum",
                "source": "official",
            },
        ],
    )

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "Macao Museum",
            "question": "Which details are worth noticing on site?",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["poi_name"] == "Macao Museum"
    assert "Macao Museum presents" in payload["text"]
    assert "Hong Kong" not in payload["text"]
    assert [source["title"] for source in payload["web_sources"]] == ["Macao Museum"]


def test_hzmb_temporal_question_uses_id_aliases_and_cross_language_query(
    monkeypatch, tmp_path
):
    _reset(monkeypatch, tmp_path)
    seen_queries: list[str] = []

    def _search(queries, **_kwargs):
        seen_queries.extend(queries)
        return [
            {
                "title": "Hong Kong-Zhuhai-Macau Bridge",
                "snippet": "The bridge and its Macao Port opened on 24 October 2018.",
                "url": "https://example.com/hzmb",
                "source": "official",
            }
        ]

    monkeypatch.setattr(guide_api, "search_web_multi", _search)
    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "poi_port_hzmb",
            "question": "这是什么时候建立的",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is True
    assert "24 October 2018" in payload["text"]
    assert payload["poi_name"] == "Hong Kong-Zhuhai-Macao Bridge Macao Port"
    assert seen_queries
    assert any(re.search(r"[\u3400-\u9fff]", query) for query in seen_queries)
    assert any(
        "Hong Kong-Zhuhai" in query and "Bridge" in query
        for query in seen_queries
    )


def test_hzmb_temporal_question_has_verified_local_fallback(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(guide_api, "search_web_multi", lambda *_args, **_kwargs: [])

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "poi_port_hzmb",
            "question": "这是什么时候建立的",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "rules"
    assert "2018" in payload["text"]
    assert "couldn't retrieve" not in payload["text"]
    assert "Border queues" not in payload["text"]
    assert "24 October 2018" in payload["text"]
    assert "。" not in payload["text"]


def test_hzmb_temporal_question_rejects_web_snippet_without_a_date(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_args, **_kwargs: [
            {
                "title": "Hong Kong-Zhuhai-Macau Bridge",
                "snippet": "The bridge is a major sea crossing in the Pearl River Delta.",
                "url": "https://example.com/hzmb",
                "source": "wikipedia:en",
            }
        ],
    )

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "poi_port_hzmb",
            "question": "这是什么时候建立的",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "rules"
    assert payload["web_used"] is False
    assert "2018" in payload["text"]


def test_detects_supported_question_languages() -> None:
    assert guide_api._detect_question_language("这个地方什么时候建立？") == "zh-CN"
    assert guide_api._detect_question_language("這個地方是甚麼時候開放的？") == "zh-TW"
    assert guide_api._detect_question_language("When did this place open?") == "en"
    assert guide_api._detect_question_language("Quando foi construído este local?") == "pt"


def test_cross_language_question_searches_all_languages_and_answers_profile_language(
    monkeypatch, tmp_path
):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(guide_api.settings, "guide_agent_enabled", True)
    _stub_local(monkeypatch, "Macao Museum", "The museum presents Macao's history.")
    translated_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        guide_api.guide_agent,
        "translate_search_queries",
        lambda question, *, input_language: translated_calls.append(
            (question, input_language)
        )
        or {
            "zh-CN": "澳门博物馆 值得看 展品",
            "en": "Macao Museum notable exhibits",
            "pt": "Museu de Macau exposições importantes",
        },
    )
    searches: list[tuple[str, list[str]]] = []

    def _search(queries, *, language, **_kwargs):
        searches.append((language, list(queries)))
        return [
            {
                "title": f"Macao Museum ({language})",
                "snippet": f"Verified museum material in {language}.",
                "url": f"https://example.com/museum/{language}",
                "source": "official",
            }
        ]

    monkeypatch.setattr(guide_api, "search_web_multi", _search)
    monkeypatch.setattr(guide_api, "filter_relevant_hits", lambda _names, hits: hits)
    agent_calls: list[dict] = []

    def _answer(*_args, **kwargs):
        agent_calls.append(kwargs)
        return SimpleNamespace(
            text="The maritime-trade gallery is a useful place to start.",
            confidence=0.86,
            language="en",
            immersive=None,
        )

    monkeypatch.setattr(guide_api.guide_agent, "answer", _answer)
    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "poi_0003",
            "question": "馆内最值得看的展品是什么？",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_language"] == "zh-CN"
    assert payload["language"] == "en"
    assert payload["source"] == "agent+web"
    assert re.search(r"[\u3400-\u9fff]", payload["text"]) is None
    assert translated_calls == [("馆内最值得看的展品是什么？", "zh-CN")]
    assert {language for language, _queries in searches} == {"zh-CN", "en", "pt"}
    assert agent_calls[0]["input_language"] == "zh-CN"
    assert agent_calls[0]["language"] == "en"


def test_cross_language_failure_never_leaks_source_language(monkeypatch, tmp_path):
    _reset(monkeypatch, tmp_path)
    monkeypatch.setattr(guide_api.settings, "guide_agent_enabled", True)
    _stub_local(monkeypatch, "Porto de Macau", "")
    monkeypatch.setattr(
        guide_api.guide_agent,
        "translate_search_queries",
        lambda *_a, **_k: {
            "zh-CN": "港珠澳大桥 建成 时间",
            "en": "bridge completion date",
            "pt": "ponte data de conclusão",
        },
    )
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda _queries, *, language, **_kwargs: [
            {
                "title": "Hong Kong-Zhuhai-Macau Bridge",
                "snippet": "The bridge opened in 2018.",
                "url": f"https://example.com/bridge/{language}",
                "source": "official",
            }
        ],
    )
    monkeypatch.setattr(guide_api, "filter_relevant_hits", lambda _names, hits: hits)
    monkeypatch.setattr(guide_api.guide_agent, "answer", lambda *_a, **_k: None)

    response = client.post(
        "/api/v1/guide/ask",
        json={
            "poi": "poi_port_hzmb",
            "question": "When did this bridge open?",
            "language": "pt",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_language"] == "en"
    assert payload["language"] == "pt"
    assert payload["source"] == "empty"
    assert payload["text"].startswith("Não consegui encontrar")
    assert "opened in 2018" not in payload["text"]
