"""Tests for postcard scene research + grounded prompts."""

from app.features.postcards.scene_library import build_slot_prompt
from app.features.postcards.scene_research import (
    local_landmarks,
    load_cached_research,
    research_poi,
    save_research,
    SceneResearch,
)


def test_local_landmarks_uses_architecture_and_tips():
    poi = {
        "id": "poi_senado",
        "name_zh": "议事亭前地",
        "district": "大堂区",
        "architecture": "黑白波浪纹碎石与喷水池",
        "observation_tips": "先看脚下碎石再看粉黄立面",
        "intro": "澳门半岛核心广场",
    }
    text = local_landmarks(poi)
    assert "议事亭前地" in text
    assert "黑白波浪纹" in text
    assert "粉黄立面" in text


def test_build_slot_prompt_requires_same_landmarks_and_ref():
    prompt = build_slot_prompt(
        poi_name="议事亭前地",
        district="大堂区",
        slot="night",
        landmarks="- 黑白波浪纹碎石\n- 中央喷水池",
        ref_image_path="/tmp/ref.jpg",
    )
    assert "固定景观锚点" in prompt
    assert "黑白波浪纹碎石" in prompt
    assert "view_image" in prompt
    assert "/tmp/ref.jpg" in prompt
    assert "只改光线" in prompt or "只改变光线" in prompt or "建筑主体不变" in prompt


def test_research_poi_offline_caches_brief(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.features.postcards.scene_research.scenes_root",
        lambda: tmp_path,
    )
    poi = {
        "id": "poi_paixao",
        "name_zh": "恋爱巷",
        "district": "花王堂区",
        "architecture": "粉红浅黄民宅窄巷",
        "observation_tips": "巷尾可瞥见大三巴",
        "intro": "短巷打卡点",
    }
    research = research_poi(poi, force=True, use_web=False)
    assert research.poi_id == "poi_paixao"
    assert "粉红浅黄" in research.landmarks
    assert (tmp_path / "poi_paixao" / "_brief.json").is_file()

    cached = load_cached_research("poi_paixao")
    assert cached is not None
    assert "恋爱巷" in cached.landmarks


def test_save_and_load_research_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.features.postcards.scene_research.scenes_root",
        lambda: tmp_path,
    )
    research = SceneResearch(
        poi_id="poi_x",
        name_zh="测试",
        landmarks="- 白墙",
        ref_image_path=None,
        sources=["pois.json"],
    )
    save_research(research)
    loaded = load_cached_research("poi_x")
    assert loaded is not None
    assert loaded.landmarks == "- 白墙"


def test_find_reference_image_uses_openverse(monkeypatch):
    from app.features.postcards import scene_research as sr

    def fake_openverse(query: str):
        if "Senado" in query:
            return (
                "https://live.staticflickr.com/example.jpg",
                "https://www.flickr.com/photos/x/1",
            )
        return None, None

    monkeypatch.setattr(sr, "_openverse_image", fake_openverse)
    monkeypatch.setattr(sr, "_wiki_summary", lambda *_a, **_k: None)
    url, page = sr.find_reference_image(
        {"name_zh": "议事亭前地", "name_en": "Senado Square"}
    )
    assert url.endswith("example.jpg")
    assert "flickr" in (page or "")
