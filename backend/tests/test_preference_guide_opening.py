from app.agents.preference_guide_agent import _build_prompt
from app.features.intent.api import _OPENERS


def test_qwenpaw_start_prompt_requires_polite_complete_duration_options():
    prompt = _build_prompt(
        action="start",
        message=None,
        language="zh-TW",
    )

    assert "礼貌欢迎" in prompt
    assert "半日、一日、多日和夜间漫游" in prompt
    assert "不要只问‘今天’" in prompt


def test_script_openers_include_multi_day_and_polite_wording():
    assert "您好" in _OPENERS["zh-CN"]
    assert "多日" in _OPENERS["zh-CN"]
    assert "您好" in _OPENERS["zh-TW"]
    assert "多日" in _OPENERS["zh-TW"]
    assert "multiple days" in _OPENERS["en"]
    assert "vários dias" in _OPENERS["pt"]
