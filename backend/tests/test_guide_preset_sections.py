"""Preset guide narration returns structured pictorial sections."""

from app.features.guide.preset_script import _load_pois, build_preset_narration


def setup_function() -> None:
    _load_pois.cache_clear()


def test_taipa_houses_sections_include_prominent_history():
    result = build_preset_narration("龙环葡韵", language="zh-CN")
    assert result is not None
    assert result["poi_name"] == "龙环葡韵"
    ids = [s["id"] for s in result["sections"]]
    assert ids == ["overview", "history", "architecture", "story"]

    history = next(s for s in result["sections"] if s["id"] == "history")
    assert "1921" in history["body"]
    assert "博物馆" in history["body"] or "住宅" in history["body"]

    overview = next(s for s in result["sections"] if s["id"] == "overview")
    assert "龙环葡韵" in overview["body"]

    # Flat text kept for TTS / legacy clients
    assert "1921" in result["text"]
    assert result["text"].startswith(overview["body"][:8])


def test_history_interest_prefixes_history_section():
    result = build_preset_narration(
        "龙环葡韵",
        language="zh-CN",
        interests=["history"],
    )
    assert result is not None
    history = next(s for s in result["sections"] if s["id"] == "history")
    assert history["body"].startswith("这段历史沿革值得细听：")


def test_next_stop_lands_in_story_section():
    result = build_preset_narration(
        "龙环葡韵",
        language="zh-CN",
        next_stop="官也街",
    )
    assert result is not None
    story = next(s for s in result["sections"] if s["id"] == "story")
    assert "官也街" in story["body"]
    assert result["next_stop"] == "官也街"


def test_generate_api_returns_sections(client=None):
    from fastapi.testclient import TestClient

    from app.main import app

    http = client or TestClient(app)
    response = http.post(
        "/api/v1/guide/generate",
        json={"poi": "龙环葡韵", "language": "zh-CN"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sections"]
    assert any(s["id"] == "history" for s in payload["sections"])
    assert payload["text"]
