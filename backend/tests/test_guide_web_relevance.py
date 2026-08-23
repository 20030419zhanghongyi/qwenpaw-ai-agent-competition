"""Dataset-wide guide relevance and foreign-language purity checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.features.guide import api as guide_api
from app.features.guide.api import GuideAskRequest, GuideRequest
from app.features.guide.preset_script import _load_pois, build_preset_narration
from app.features.guide.web_search import filter_relevant_hits


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "pois.json"
UNRELATED_HITS = [
    {
        "title": "Hong Kong",
        "snippet": "Hong Kong is a special administrative region on China's southern coast.",
        "url": "https://example.com/hong-kong",
        "source": "test",
    },
    {
        "title": "National Museum of Brazil fire",
        "snippet": "The National Museum of Brazil was heavily damaged by a large fire.",
        "url": "https://example.com/brazil-museum",
        "source": "test",
    },
]


def _pois() -> list[dict]:
    return list(json.loads(DATA_PATH.read_text(encoding="utf-8"))["pois"])


def test_every_poi_rejects_unrelated_web_results() -> None:
    pois = _pois()
    assert len(pois) == 352
    for poi in pois:
        names = [poi.get("name_zh"), poi.get("name_en"), poi.get("name_pt")]
        for name in (str(value).strip() for value in names if value):
            assert filter_relevant_hits(name, UNRELATED_HITS) == [], poi["id"]


def test_every_poi_accepts_a_result_named_for_that_place() -> None:
    for poi in _pois():
        names = [poi.get("name_zh"), poi.get("name_en"), poi.get("name_pt")]
        for name in (str(value).strip() for value in names if value):
            hit = {
                "title": name,
                "snippet": f"Visitor information for {name} in Macau.",
                "url": f"https://example.com/{poi['id']}",
                "source": "test",
            }
            assert filter_relevant_hits(name, [hit]) == [hit], poi["id"]


def test_every_poi_foreign_preset_is_free_of_chinese_source_text() -> None:
    _load_pois.cache_clear()
    for poi in _pois():
        for language in ("en", "pt"):
            result = build_preset_narration(poi["id"], language=language)
            assert result is not None, (poi["id"], language)
            public_text = json.dumps(
                {
                    "text": result["text"],
                    "immersive": result["immersive"],
                    "sections": result["sections"],
                },
                ensure_ascii=False,
            )
            assert re.search(r"[\u3400-\u9fff]", public_text) is None, (
                poi["id"],
                language,
            )


def test_every_poi_resolves_every_available_canonical_name() -> None:
    """Every supported name must resolve to one of its canonical POI records."""
    _load_pois.cache_clear()
    ids_by_name: dict[str, set[str]] = {}
    for poi in _pois():
        for key in ("name_zh", "name_en", "name_pt", "alias"):
            name = str(poi.get(key) or "").strip()
            if name:
                ids_by_name.setdefault(name, set()).add(poi["id"])

    for poi in _pois():
        by_id = build_preset_narration(poi["id"], language="zh-CN")
        assert by_id is not None, poi["id"]
        assert by_id["poi_id"] == poi["id"], poi["id"]

        queries = [
            str(poi[key]).strip()
            for key in ("name_zh", "name_en", "name_pt", "alias")
            if poi.get(key)
        ]
        for query in queries:
            result = build_preset_narration(query, language="zh-CN")
            assert result is not None, (poi["id"], query)
            assert result["poi_id"] in ids_by_name[query], (poi["id"], query)


def test_canonical_name_collisions_are_explicit() -> None:
    """Keep duplicate names visible until the source records are reconciled."""
    collisions: dict[tuple[str, str], list[str]] = {}
    for key in ("name_zh", "name_en", "name_pt", "alias"):
        ids_by_name: dict[str, list[str]] = {}
        for poi in _pois():
            name = str(poi.get(key) or "").strip()
            if name:
                ids_by_name.setdefault(name, []).append(poi["id"])
        collisions.update(
            {
                (key, name): ids
                for name, ids in ids_by_name.items()
                if len(ids) > 1
            }
        )

    assert collisions == {
        ("name_zh", "明记牛杂"): ["poi_0080", "poi_0091"],
        ("name_en", "Fire Services Museum"): [
            "poi_0149",
            "poi_cultural_fire_services_museum",
        ],
        ("name_pt", "Museu dos Bombeiros"): [
            "poi_0149",
            "poi_cultural_fire_services_museum",
        ],
    }


def test_every_poi_generates_complete_guide_in_every_language(monkeypatch) -> None:
    """Exercise the real generate handler for all 352 POIs in all UI languages."""
    monkeypatch.setattr(guide_api, "record_trace", lambda **_: None)
    _load_pois.cache_clear()

    for poi in _pois():
        for language in ("zh-CN", "zh-TW", "en", "pt"):
            result = guide_api.generate(
                GuideRequest(poi=poi["id"], language=language),
                enhance=False,
            )
            assert result["poi_id"] == poi["id"], (poi["id"], language)
            assert result["language"] == language, (poi["id"], language)
            assert str(result["poi_name"]).strip(), (poi["id"], language)
            assert str(result["text"]).strip(), (poi["id"], language)
            assert str(result["audio_script"]).strip(), (poi["id"], language)
            assert result["sections"], (poi["id"], language)
            assert result["immersive"]["title"], (poi["id"], language)
            if language in {"en", "pt"}:
                public_text = json.dumps(result, ensure_ascii=False)
                assert re.search(r"[\u3400-\u9fff]", public_text) is None, (
                    poi["id"],
                    language,
                )


def test_every_poi_ask_discards_other_place_results(monkeypatch) -> None:
    """Exercise the ask handler for every POI with relevant and adversarial hits."""
    monkeypatch.setattr(guide_api, "record_trace", lambda **_: None)
    monkeypatch.setattr(
        guide_api,
        "_apply_review",
        lambda text, *, path: (text, {"decision": "pass", "source": "test"}),
    )
    _load_pois.cache_clear()

    current_hits: list[dict[str, str]] = []
    monkeypatch.setattr(
        guide_api,
        "search_web_multi",
        lambda *_args, **_kwargs: [*UNRELATED_HITS, *current_hits],
    )

    for poi in _pois():
        canonical_name = str(poi.get("name_zh") or poi["id"]).strip()
        relevant_hit = {
            "title": canonical_name,
            "snippet": "This source describes the selected place in Macau and its local history.",
            "url": f"https://example.com/{poi['id']}",
            "source": "test",
        }
        current_hits[:] = [relevant_hit]

        result = guide_api.ask(
            GuideAskRequest(
                poi=poi["id"],
                question="What should I notice at this place?",
                language="en",
            ),
            enhance=False,
            web=True,
        )

        assert result["web_used"] is True, poi["id"]
        assert result["source"] == "web", poi["id"]
        assert result["web_sources"] == [
            {
                "title": canonical_name,
                "url": relevant_hit["url"],
                "source": "test",
            }
        ], poi["id"]
        assert "Hong Kong" not in result["text"], poi["id"]
        assert "National Museum of Brazil" not in result["text"], poi["id"]
