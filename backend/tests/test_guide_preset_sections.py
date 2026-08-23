"""Preset guide narration returns immersive companion + legacy sections."""

import json
import re

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


def test_immersive_schema_mapped_from_poi_fields():
    result = build_preset_narration("龙环葡韵", language="zh-CN", interests=["photo"])
    assert result is not None
    imm = result["immersive"]
    assert imm["title"] == "龙环葡韵"
    assert imm["subtitle"]
    assert imm["hook"]
    assert imm["why_it_matters"]
    assert imm["historical_story"]
    assert "1921" in imm["historical_story"]
    assert isinstance(imm["things_to_observe"], list)
    assert 1 <= len(imm["things_to_observe"]) <= 5
    for item in imm["things_to_observe"]:
        assert item["observation"]
        assert item["explanation"]
    assert imm["local_story"]
    assert imm["interactive_suggestion"]
    assert imm["audio_script"]
    assert result["audio_script"] == imm["audio_script"]
    assert result["text"] == imm["audio_script"]
    # photo interest → photo-flavored interactive
    assert "拍" in imm["interactive_suggestion"] or "角度" in imm["interactive_suggestion"]


def test_english_preset_never_splices_chinese_source_text():
    result = build_preset_narration("大三巴牌坊", language="en")
    assert result is not None
    assert result["poi_name"] == "Ruins of St. Paul's"
    public_text = json.dumps(
        {
            "text": result["text"],
            "audio_script": result["audio_script"],
            "immersive": result["immersive"],
            "sections": result["sections"],
        },
        ensure_ascii=False,
    )
    assert re.search(r"[\u3400-\u9fff]", public_text) is None
    assert "History" in result["immersive"]["subtitle"]


def test_portuguese_preset_uses_portuguese_name_and_no_chinese_source_text():
    result = build_preset_narration("大三巴牌坊", language="pt")
    assert result is not None
    assert result["poi_name"] == "Ruínas de S. Paulo"
    public_text = json.dumps(
        {
            "text": result["text"],
            "audio_script": result["audio_script"],
            "immersive": result["immersive"],
            "sections": result["sections"],
        },
        ensure_ascii=False,
    )
    assert re.search(r"[\u3400-\u9fff]", public_text) is None
    assert "História" in result["immersive"]["subtitle"]


def test_foreign_presets_sound_conversational_and_avoid_mechanical_bridges():
    english = build_preset_narration("大三巴牌坊", language="en")
    portuguese = build_preset_narration("大三巴牌坊", language="pt")

    assert english is not None and portuguese is not None
    assert english["immersive"]["hook"].startswith("Here we are at")
    assert "So, why is this place worth stopping for?" in english["immersive"][
        "why_it_matters"
    ]
    assert "In Macau’s urban memory" not in english["text"]
    assert "In the past," not in english["text"]
    assert "1835" in english["immersive"]["historical_story"]
    assert "Aqui estamos" in portuguese["immersive"]["hook"]
    assert "No passado," not in portuguese["text"]
    assert "1835" in portuguese["immersive"]["historical_story"]


def test_history_interest_prefixes_history_section():
    result = build_preset_narration(
        "龙环葡韵",
        language="zh-CN",
        interests=["history"],
    )
    assert result is not None
    history = next(s for s in result["sections"] if s["id"] == "history")
    assert history["body"].startswith("这段历史沿革值得细听：")
    assert result["immersive"]["historical_story"].startswith("这段历史沿革值得细听：")


def test_next_stop_lands_in_story_and_next_exploration():
    result = build_preset_narration(
        "龙环葡韵",
        language="zh-CN",
        next_stop="官也街",
        next_distance="约 400 米",
        next_walk_time="约 6 分钟",
    )
    assert result is not None
    story = next(s for s in result["sections"] if s["id"] == "story")
    assert "官也街" in story["body"]
    assert result["next_stop"] == "官也街"
    nxt = result["immersive"]["next_exploration"]
    assert nxt["location"] == "官也街"
    assert nxt["distance"] == "约 400 米"
    assert nxt["walk_time"] == "约 6 分钟"
    assert nxt["reason"]


def test_family_travel_type_personalizes_interactive():
    result = build_preset_narration(
        "议事亭前地",
        language="zh-CN",
        travel_type=["family"],
    )
    assert result is not None
    assert "同行" in result["immersive"]["interactive_suggestion"] or "家人" in result[
        "immersive"
    ]["interactive_suggestion"]


def test_generate_api_returns_immersive_and_sections(client=None):
    from fastapi.testclient import TestClient

    from app.main import app

    http = client or TestClient(app)
    response = http.post(
        "/api/v1/guide/generate",
        json={"poi": "龙环葡韵", "language": "zh-CN", "interests": ["history"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sections"]
    assert any(s["id"] == "history" for s in payload["sections"])
    assert payload["text"]
    assert payload["audio_script"]
    assert payload["immersive"]["title"]
    assert payload["immersive"]["hook"]
    assert payload["immersive"]["things_to_observe"]


def test_senado_immersive_is_richer_than_one_liners():
    """议事亭：字段充实后 immersive 应明显长于「一句一块」，观察 ≥3。"""
    result = build_preset_narration(
        "议事亭前地",
        language="zh-CN",
        interests=["history", "architecture"],
    )
    assert result is not None
    imm = result["immersive"]
    assert result["poi_id"] == "poi_senado"
    assert len(imm["hook"]) >= 40
    assert len(imm["why_it_matters"]) >= 40
    assert len(imm["historical_story"]) >= 60
    assert "1993" in imm["historical_story"] or "1993" in result["text"]
    assert "今日" in imm["historical_story"] or "今天" in imm["historical_story"]
    obs = imm["things_to_observe"]
    assert 3 <= len(obs) <= 5
    assert any("碎石" in o["observation"] or "波浪" in o["observation"] for o in obs)
    assert any("喷水" in o["observation"] or "立面" in o["observation"] for o in obs)
    assert len(imm["local_story"]) >= 40
    assert len(imm["interactive_suggestion"]) >= 40
    assert len(imm["audio_script"]) >= 200
    # Legacy sections still present for old clients
    assert [s["id"] for s in result["sections"]] == [
        "overview",
        "history",
        "architecture",
        "story",
    ]
    # Soft photo tip must not hard-code a clock time as fact
    assert "9 点" not in imm["audio_script"]
    assert "以现场为准" in result["text"] or "以現場為準" in result["text"]


def test_generate_api_senado_returns_immersive(client=None):
    from fastapi.testclient import TestClient

    from app.main import app

    http = client or TestClient(app)
    response = http.post(
        "/api/v1/guide/generate",
        json={
            "poi": "议事亭前地",
            "language": "zh-CN",
            "interests": ["history", "architecture"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "immersive" in payload
    imm = payload["immersive"]
    assert imm["hook"]
    assert imm["why_it_matters"]
    assert len(imm["things_to_observe"]) >= 3
    assert payload["sections"]
    assert payload["text"] == payload["audio_script"] or payload["audio_script"]
