"""Guide confidence fallback, TTS contract, and guardrail tests."""

import json

import pytest
from fastapi.testclient import TestClient

from app.agents.photo_agent import PhotoRecognition
from app.features.guide import api as guide_api
from app.features.intent import api as intent_api
from app.guardrails.runtime import rate_limiter
from app.main import app
from app.observability import trace

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_guardrails(monkeypatch, tmp_path):
    rate_limiter.clear()
    monkeypatch.setattr(intent_api, "record_trace", lambda **_: None)
    monkeypatch.setattr(trace, "_trace_path", lambda: tmp_path / "trace.jsonl")
    yield
    rate_limiter.clear()


def _photo_response(monkeypatch, recognition: PhotoRecognition | None):
    monkeypatch.setattr(guide_api.settings, "photo_agent_enabled", True)
    monkeypatch.setattr(guide_api, "scrub", lambda raw: raw)
    monkeypatch.setattr(guide_api.photo_agent, "recognize", lambda *_args, **_kwargs: recognition)
    return client.post(
        "/api/v1/guide/photo",
        files={"file": ("photo.jpg", b"fake-image", "image/jpeg")},
    )


def test_photo_low_confidence_returns_safe_manual_selection(monkeypatch):
    monkeypatch.setattr(guide_api, "_explain", lambda *_args, **_kwargs: pytest.fail("must not explain"))
    response = _photo_response(
        monkeypatch,
        PhotoRecognition(description="模糊的街道建筑画面，无法确认具体地点。", candidate_poi="大三巴牌坊", confidence=0.59),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recognition_status"] == "uncertain"
    assert payload["candidate_poi"] is None
    assert "未能确定" in payload["low_confidence_hint"]
    assert payload["next_actions"] == ["retake", "manual_select"]
    assert payload["explanation"] is None


def test_photo_high_confidence_keeps_identified_result(monkeypatch):
    monkeypatch.setattr(guide_api, "_explain", lambda *_args, **_kwargs: None)
    response = _photo_response(
        monkeypatch,
        PhotoRecognition(description="石质巴洛克立面与十字架。", candidate_poi="大三巴牌坊", confidence=0.9),
    )

    assert response.status_code == 200
    assert response.json()["recognition_status"] == "identified"
    assert response.json()["candidate_poi"] == "大三巴牌坊"


def test_tts_contract_uses_fixed_voice_and_no_object_key(monkeypatch):
    monkeypatch.setattr(
        guide_api,
        "synthesize_to_oss",
        lambda text, language: {
            "audio_url": "https://oss.example/signed.mp3?token=secret",
            "object_key": "tts/private.mp3",
            "voice": "Rocky",
            "content_type": "audio/mpeg",
            "expires_in": 3600,
        },
    )
    response = client.post("/api/v1/guide/tts", json={"text": "欢迎来到澳门。", "language": "yue"})

    assert response.status_code == 200
    assert response.json() == {
        "audio_url": "https://oss.example/signed.mp3?token=secret",
        "expires_in": 3600,
        "content_type": "audio/mpeg",
        "language": "yue",
        "voice": "Rocky",
    }


def test_tts_rejects_unsupported_language_and_reports_unavailable(monkeypatch):
    assert client.post("/api/v1/guide/tts", json={"text": "hello", "language": "ja"}).status_code == 422
    monkeypatch.setattr(guide_api, "synthesize_to_oss", lambda *_args: (_ for _ in ()).throw(guide_api.TTSUnavailableError("missing")))
    response = client.post("/api/v1/guide/tts", json={"text": "hello", "language": "en"})
    assert response.status_code == 503


def test_intent_rate_limit_returns_retry_after():
    for _ in range(20):
        assert client.post("/api/v1/intent/parse", json={"text": "下午少走路"}).status_code == 200
    limited = client.post("/api/v1/intent/parse", json={"text": "下午少走路"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1


def test_trace_redacts_raw_input_and_output(tmp_path, monkeypatch):
    target = tmp_path / "trace.jsonl"
    monkeypatch.setattr(trace, "_trace_path", lambda: target)
    trace.record_trace(kind="test", input_summary="private route instruction", output_summary="private narration")
    event = json.loads(target.read_text().strip())
    assert "private route instruction" not in target.read_text()
    assert "private narration" not in target.read_text()
    assert event["input_chars"] == len("private route instruction")
    assert event["output_chars"] == len("private narration")
