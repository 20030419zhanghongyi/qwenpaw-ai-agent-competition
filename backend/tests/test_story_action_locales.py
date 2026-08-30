"""Shared action localization, using each story's existing display content."""

from copy import deepcopy
from datetime import datetime, timezone
import re
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app.core.security import require_user_id
from app.features.stories import api
from app.features.stories.content import (
    chapter_by_id,
    load_story,
    localize_story,
    story_nodes,
)
from app.features.stories.engine import apply_action
from app.features.stories.models import StoryActionRequest, StorySession, StorySessionState
from app.features.stories.service import StoryService
from app.main import app


STORY_IDS = ("lotus_city_double_map", "taipa_letters", "coloane_after_tide")
LANGUAGES = ("zh-CN", "zh-TW", "en", "pt", "unsupported")
PUZZLES = [
    (story_id, node["id"])
    for story_id in STORY_IDS
    for node in story_nodes(load_story(story_id))
    if node["kind"] == "puzzle"
]
HINT_MESSAGES = {
    "zh-CN": "已提供提示",
    "zh-TW": "已提供提示",
    "en": "Here is your hint.",
    "pt": "Aqui está a sua pista.",
}
WRONG_MESSAGES = {
    "zh-CN": "答案不正确，可以重试、查看提示或跳过",
    "zh-TW": "答案不正確，可以重試、查看提示或略過",
    "en": "Not quite. You can try again, ask for a hint, or skip this puzzle.",
    "pt": "Ainda não é a resposta certa. Pode tentar de novo, pedir uma pista ou saltar.",
}


def _session(story: dict, chapter_id: str) -> StorySession:
    now = datetime.now(timezone.utc)
    return StorySession(
        session_id="localized-story-session",
        user_id="localized-story-user",
        story_id=story["id"],
        trip_id="localized-story-trip",
        current_chapter_id=chapter_id,
        status="active",
        state=StorySessionState(content_version=story["version"]),
        created_at=now,
        updated_at=now,
    )


def _act(story, session, action, language, **values):
    request = StoryActionRequest(
        action=action, chapter_id=session.current_chapter_id, **values
    )
    result = apply_action(story, session, request)
    service = StoryService(repository=Mock(), trips=Mock())
    response = service._action_response(story, session, result, language=language)
    assert "solution" not in response.model_dump_json()
    return response, result


@pytest.mark.parametrize(("story_id", "chapter_id"), PUZZLES)
@pytest.mark.parametrize("language", LANGUAGES)
def test_all_puzzle_hints_and_answer_feedback_follow_locale(story_id, chapter_id, language):
    story = load_story(story_id)
    original = deepcopy(story)
    session = _session(story, chapter_id)
    _act(story, session, "arrive", language)
    localized_puzzle = chapter_by_id(localize_story(story, language), chapter_id)["puzzle"]
    source_puzzle = chapter_by_id(story, chapter_id)["puzzle"]
    locale = language if language in HINT_MESSAGES else "zh-CN"

    wrong, _ = _act(story, session, "answer", language, answer="not-an-answer")
    assert not wrong.accepted
    assert wrong.message == WRONG_MESSAGES[locale]
    assert wrong.hint is None
    assert session.state.attempts[chapter_id] == 1

    # Hints advance one tier at a time, then repeat the last tier without advancing.
    hints = localized_puzzle["hints"]
    for index in range(len(hints) + 2):
        hinted, result = _act(story, session, "hint", language)
        assert hinted.hint == hints[min(index, len(hints) - 1)]
        assert hinted.message == HINT_MESSAGES[locale]
        assert result.hint == source_puzzle["hints"][min(index, len(hints) - 1)]
        assert session.state.hint_counts[chapter_id] == index + 1
        assert session.current_chapter_id == chapter_id
        assert not hinted.new_rewards

    solved, _ = _act(story, session, "answer", language, answer=source_puzzle["solution"])
    assert solved.accepted
    assert solved.message == localized_puzzle["explanation"]
    assert solved.hint is None
    assert solved.session.current_chapter_id != chapter_id
    assert chapter_id in session.state.completed_chapter_ids
    assert len(solved.new_rewards) == 1
    assert story == original


@pytest.mark.parametrize(("story_id", "chapter_id"), PUZZLES)
@pytest.mark.parametrize("language", LANGUAGES)
def test_skip_feedback_comes_from_submitted_chapter_not_next_chapter(story_id, chapter_id, language):
    story = load_story(story_id)
    session = _session(story, chapter_id)
    _act(story, session, "arrive", language)
    localized_puzzle = chapter_by_id(localize_story(story, language), chapter_id)["puzzle"]

    skipped, _ = _act(story, session, "skip", language)

    assert skipped.accepted
    assert skipped.message == localized_puzzle["skip_text"]
    assert skipped.session.current_chapter_id != chapter_id
    assert chapter_id in session.state.skipped_chapter_ids
    assert len(skipped.new_rewards) == 1
    state_before_retry = session.model_copy(deep=True)
    repeated = apply_action(story, session, StoryActionRequest(action="skip", chapter_id=chapter_id))
    response = StoryService(repository=Mock(), trips=Mock())._action_response(
        story, session, repeated, language=language
    )
    assert repeated.message_key == "chapter_already_processed"
    assert not repeated.changed
    assert not response.new_rewards
    assert session == state_before_retry
    if language in ("en", "pt"):
        assert not re.search(r"[\u3400-\u9fff]", response.message)


@pytest.mark.parametrize("story_id", STORY_IDS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_continue_ending_and_repeat_feedback_follow_locale(story_id, language):
    story = load_story(story_id)
    nodes = story_nodes(story)
    session = _session(story, nodes[0]["id"])
    continued, _ = _act(story, session, "continue", language)

    session.current_chapter_id = nodes[-1]["id"]
    _act(story, session, "arrive", language)
    values = {"choice_id": story["endings"][0]["id"], "reflection": "My original note 原文"}
    completed, _ = _act(story, session, "choose_ending", language, **values)
    repeated, result = _act(story, session, "choose_ending", language, **values)
    assert session.state.ending_reflection == values["reflection"]
    assert not result.changed
    assert not repeated.new_rewards
    for response in (continued, completed, repeated):
        assert response.accepted
        if language in ("en", "pt"):
            assert not re.search(r"[\u3400-\u9fff]", response.message)
    if language == "zh-TW":
        assert continued.message == "劇情已繼續"
        assert completed.message == "今日補記已儲存，故事完成"
        assert repeated.message == "此結局已儲存"


@pytest.mark.parametrize("story_id", STORY_IDS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_action_api_localizes_hint_and_feedback_without_persisting_translations(
    monkeypatch, story_id, language
):
    story = load_story(story_id)
    chapter = story_nodes(story)[1]
    session = _session(story, chapter["id"])
    session.state.arrived_chapter_ids.append(chapter["id"])
    repository = Mock()
    repository.get.return_value = session
    repository.save.side_effect = lambda updated: updated
    monkeypatch.setattr(api, "story_service", StoryService(repository, Mock()))
    monkeypatch.setitem(app.dependency_overrides, require_user_id, lambda: session.user_id)
    client = TestClient(app)
    url = f"/api/v1/story-sessions/{session.session_id}/actions?language={language}"

    hint = client.post(url, json={"action": "hint", "chapter_id": chapter["id"]})
    assert hint.status_code == 200
    localized = chapter_by_id(localize_story(story, language), chapter["id"])["puzzle"]
    assert hint.json()["hint"] == localized["hints"][0]
    skipped = client.post(url, json={"action": "skip", "chapter_id": chapter["id"]})
    assert skipped.status_code == 200
    assert skipped.json()["message"] == localized["skip_text"]
    assert session.state.rewards[0].text == chapter["puzzle"]["reward"]["text"]
    assert repository.save.call_count == 2
    assert "solution" not in hint.text + skipped.text
    assert "hint_index" not in hint.json()  # Display references stay internal.


@pytest.mark.parametrize("story_id", STORY_IDS)
def test_switching_hint_language_keeps_server_hint_tier(story_id):
    story = load_story(story_id)
    chapter = story_nodes(story)[1]
    session = _session(story, chapter["id"])
    _act(story, session, "arrive", "zh-CN")
    for index, language in enumerate(("en", "pt", "zh-TW", "zh-CN")):
        response, _ = _act(story, session, "hint", language)
        hints = chapter_by_id(localize_story(story, language), chapter["id"])["puzzle"]["hints"]
        assert response.hint == hints[min(index, len(hints) - 1)]
        assert session.state.hint_counts[chapter["id"]] == index + 1


def test_shared_action_localization_does_not_require_a_story_id_allowlist():
    # A package without an overlay still localizes shared feedback while keeping
    # its authored hints and explanation as the normal missing-translation fallback.
    story = load_story("lotus_city_double_map")
    story["id"] = "new_story_without_locale_overlay"
    chapter = story_nodes(story)[1]
    session = _session(story, chapter["id"])
    _act(story, session, "arrive", "en")
    wrong, _ = _act(story, session, "answer", "en", answer="wrong")
    hinted, _ = _act(story, session, "hint", "en")
    skipped, _ = _act(story, session, "skip", "en")

    assert wrong.message == WRONG_MESSAGES["en"]
    assert hinted.message == HINT_MESSAGES["en"]
    assert hinted.hint == chapter["puzzle"]["hints"][0]
    assert skipped.message == chapter["puzzle"]["skip_text"]
