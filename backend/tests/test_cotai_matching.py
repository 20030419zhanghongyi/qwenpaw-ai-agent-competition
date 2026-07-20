"""Cotai region templates should rank equally when theme=cotai."""

from app.features.routes.matcher import (
    _COTAI_REGION_BONUS,
    _HEAT_SCORE_CAP,
    _PRESET_SCORE_CAP,
    score_template_preference,
)
from app.models.user import Preference


def _tpl(template_id: str, theme: str, *, heat_nodes: list[str] | None = None) -> dict:
    nodes = [{"poi_id": pid, "order": i + 1} for i, pid in enumerate(heat_nodes or ["poi_x"])]
    return {
        "id": template_id,
        "theme": theme,
        "duration_label": "半日",
        "duration_hours": 4.0,
        "physical_level": "low",
        "suitable_for": ["photo", "architecture", "friends", "family", "relax"],
        "nodes": nodes,
    }


def test_cotai_theme_gives_equal_score_to_strip_and_studio_city_variants():
    pref = Preference(
        duration="half-day",
        interests=["photo"],
        themes=["cotai"],
        travel_type=["solo"],
        physical=["normal"],
        language="zh-CN",
    )
    # Even with very different fake heat maps, Cotai variants must tie.
    heat = {"poi_hot_a": 40, "poi_hot_b": 1, "poi_hot_c": 1}
    gold, gold_reasons = score_template_preference(
        _tpl("cotai_theme_europe_halfday", "摄影", heat_nodes=["poi_hot_b", "poi_hot_c"]),
        pref,
        poi_heat=heat,
    )
    studio, studio_reasons = score_template_preference(
        _tpl("cotai_resort_show_halfday", "休闲", heat_nodes=["poi_hot_a"]),
        pref,
        poi_heat=heat,
    )
    assert gold == studio
    assert any("同权" in r for r in gold_reasons)
    assert any("同权" in r for r in studio_reasons)
    # Cotai region fills the shared preset budget; interests/ports still move rankings.
    assert _COTAI_REGION_BONUS == _PRESET_SCORE_CAP == 12


def test_cotai_theme_outranks_hot_peninsula_template():
    pref = Preference(
        duration="half-day",
        interests=["photo"],
        themes=["cotai"],
        travel_type=["solo"],
        physical=["normal"],
        language="zh-CN",
    )
    heat = {"poi_a": 50, "poi_b": 50}
    cotai, _ = score_template_preference(
        _tpl("cotai_theme_europe_halfday", "摄影"),
        pref,
        poi_heat=heat,
    )
    heritage, heritage_reasons = score_template_preference(
        {
            "id": "heritage_fullday",
            "theme": "文化",
            "duration_label": "一日",
            "duration_hours": 8.0,
            "physical_level": "medium",
            "suitable_for": ["photo", "history"],
            "nodes": [{"poi_id": "poi_a", "order": 1}, {"poi_id": "poi_b", "order": 2}],
        },
        pref,
        poi_heat=heat,
    )
    assert cotai > heritage
    assert any("半岛线降权" in r for r in heritage_reasons)


def test_offline_heat_is_capped_below_preference_signals():
    """A long hot peninsula template must not outscore a clear interest match via heat alone."""
    pref = Preference(
        duration="half-day",
        interests=["photo"],
        themes=[],
        travel_type=["friends"],
        physical=["normal"],
        language="zh-CN",
    )
    hot_nodes = [f"poi_hot_{i}" for i in range(12)]
    heat = {pid: 3 for pid in hot_nodes}
    hot_tpl, hot_reasons = score_template_preference(
        {
            "id": "heritage_fullday",
            "theme": "文化",
            "duration_label": "一日",
            "duration_hours": 8.0,
            "physical_level": "medium",
            "suitable_for": ["history"],
            "nodes": [{"poi_id": pid, "order": i + 1} for i, pid in enumerate(hot_nodes)],
        },
        pref,
        poi_heat=heat,
    )
    photo_tpl, _ = score_template_preference(
        _tpl("photo_halfday", "摄影", heat_nodes=["poi_cold"]),
        pref,
        poi_heat={"poi_cold": 0},
    )
    assert any("弱化" in r for r in hot_reasons)
    # Raw heat sum would be 36; after //2 + subcap the heat-only template stays ≤ heat subcap.
    assert hot_tpl <= _HEAT_SCORE_CAP
    assert photo_tpl > hot_tpl


def test_preset_template_signals_are_capped_at_twelve():
    """Duration + theme + Cotai + physical + heat share one ≤12 preset budget."""
    pref = Preference(
        duration="half-day",
        interests=["photo", "architecture"],
        themes=["cotai", "photo"],
        travel_type=["friends"],
        physical=["less-walk"],
        language="zh-CN",
    )
    # Cotai + duration + physical would exceed 12 without the shared cap.
    score, reasons = score_template_preference(
        _tpl("cotai_theme_europe_halfday", "摄影"),
        pref,
        poi_heat={"poi_x": 99},
    )
    # Interests (photo+architecture)×2 + travel friends = 5 extras beyond preset.
    interest_travel = 2 * 2 + 1
    assert score == _PRESET_SCORE_CAP + interest_travel
    assert any("压缩" in r for r in reasons)


def test_interest_match_outweighs_template_theme_tag():
    pref = Preference(
        duration="half-day",
        interests=["food"],
        themes=["heritage"],
        travel_type=["solo"],
        physical=["normal"],
        language="zh-CN",
    )
    foodish, _ = score_template_preference(
        {
            "id": "food_family_halfday",
            "theme": "美食",
            "duration_label": "半日",
            "duration_hours": 3.0,
            "physical_level": "low",
            "suitable_for": ["food", "family"],
            "nodes": [{"poi_id": "poi_x", "order": 1}],
        },
        pref,
    )
    heritage_theme_only, _ = score_template_preference(
        {
            "id": "culture_halfday",
            "theme": "文化",
            "duration_label": "一日",
            "duration_hours": 7.0,
            "physical_level": "medium",
            "suitable_for": ["history"],
            "nodes": [{"poi_id": "poi_y", "order": 1}],
        },
        pref,
    )
    assert foodish > heritage_theme_only
