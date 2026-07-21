"""guide_agent coerces legacy flat text and new immersive JSON."""

from app.agents.guide_agent import _coerce


def test_coerce_legacy_flat_text():
    expl = _coerce(
        {
            "text": "这是一段旧版讲解。",
            "source_type": "official",
            "confidence": 0.9,
            "ai_generated": True,
            "language": "zh-CN",
        }
    )
    assert expl.text.startswith("这是一段")
    assert expl.immersive is not None
    assert expl.immersive.audio_script == expl.text
    assert expl.immersive.hook == expl.text


def test_coerce_immersive_payload():
    expl = _coerce(
        {
            "title": "议事亭前地",
            "subtitle": "历史 · 建筑",
            "hook": "钩子一句。",
            "why_it_matters": "因为重要。",
            "historical_story": "从前到今天。",
            "things_to_observe": [
                {"observation": "波浪地面", "explanation": "葡式石仔路"}
            ],
            "local_story": "节庆故事。",
            "interactive_suggestion": "停三十秒。",
            "next_exploration": {
                "location": "玫瑰堂",
                "distance": "",
                "walk_time": "",
                "reason": "接着听。",
            },
            "audio_script": "朗读稿全文。",
            "text": "朗读稿全文。",
            "source_type": "official",
            "confidence": 0.88,
            "ai_generated": True,
            "language": "zh-CN",
        }
    )
    assert expl.immersive is not None
    assert expl.immersive.title == "议事亭前地"
    assert expl.immersive.things_to_observe[0].observation == "波浪地面"
    assert expl.immersive.next_exploration.location == "玫瑰堂"
    assert expl.text == "朗读稿全文。"
    assert expl.source_type == "official"
