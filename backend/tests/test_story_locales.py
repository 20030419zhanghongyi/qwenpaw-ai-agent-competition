import re

import pytest

from app.features.stories.content import (
    load_story,
    localize_story,
    public_story,
    story_nodes,
)


STORY_IDS = (
    "lotus_city_double_map",
    "taipa_letters",
    "coloane_after_tide",
)
HAN_TEXT = re.compile(r"[\u3400-\u9fff]")


def _strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)
    elif isinstance(value, str):
        yield value


def _puzzle_solutions(story):
    return [
        node.get("puzzle", {}).get("solution")
        for node in story_nodes(story)
        if node.get("puzzle")
    ]


@pytest.mark.parametrize("story_id", STORY_IDS)
@pytest.mark.parametrize("language", ("en", "pt"))
def test_story_public_content_has_no_chinese_fallback(story_id, language):
    localized = public_story(localize_story(load_story(story_id), language))

    assert not [text for text in _strings(localized) if HAN_TEXT.search(text)]


@pytest.mark.parametrize("story_id", STORY_IDS)
@pytest.mark.parametrize("language", ("zh-TW", "en", "pt"))
def test_story_localization_preserves_structure_and_answers(story_id, language):
    source = load_story(story_id)
    localized = localize_story(source, language)

    assert localized["id"] == source["id"]
    assert localized["route_id"] == source["route_id"]
    assert [node["id"] for node in story_nodes(localized)] == [
        node["id"] for node in story_nodes(source)
    ]
    assert _puzzle_solutions(localized) == _puzzle_solutions(source)
    assert localized["title"] != source["title"]
