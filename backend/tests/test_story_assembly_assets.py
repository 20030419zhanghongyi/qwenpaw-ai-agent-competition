"""Keep the public Lou Kau puzzle aligned with the shipped frontend pieces."""

from datetime import datetime, timezone
from pathlib import Path
import re
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app.core.security import require_user_id
from app.features.stories import api
from app.features.stories.content import chapter_by_id, load_story
from app.features.stories.engine import apply_action
from app.features.stories.models import StoryActionRequest, StorySession, StorySessionState
from app.features.stories.service import StoryService
from app.main import app


STORY_ID = "lotus_city_double_map"
CHAPTER_ID = "chapter_lou_kau"
CORRECT_PIECES = ["upper_frame", "lower_frame", "oyster_shell_panel", "wooden_shutter"]
DISTRACTOR_ASSETS = {"stone_lattice": "V4-LOU-P08", "aluminum_frame": "V4-LOU-P07"}
DISTRACTOR_LABELS = {
    "zh-CN": ["石花格", "铝框"],
    "zh-TW": ["石花格", "鋁框"],
    "en": ["Stone lattice", "Aluminium frame"],
    "pt": ["Gelosia de pedra", "Moldura de alumínio"],
}


def _session() -> StorySession:
    now = datetime.now(timezone.utc)
    return StorySession(
        session_id="assembly-asset-test",
        user_id="assembly-asset-user",
        story_id=STORY_ID,
        trip_id="assembly-asset-trip",
        current_chapter_id=CHAPTER_ID,
        status="active",
        state=StorySessionState(content_version=4, arrived_chapter_ids=[CHAPTER_ID]),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize("language", DISTRACTOR_LABELS)
def test_lou_kau_api_options_resolve_to_shipped_images_in_every_language(monkeypatch, language):
    # Keep the actual API, service and content loader; isolate storage and authentication.
    session = _session()
    repository = Mock()
    repository.get.return_value = session
    monkeypatch.setattr(api, "story_service", StoryService(repository, Mock()))
    monkeypatch.setitem(app.dependency_overrides, require_user_id, lambda: session.user_id)
    client = TestClient(app)

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    fallback_source = (frontend / "src/features/story/puzzles/AssemblyPuzzle.tsx").read_text(
        encoding="utf-8"
    )
    fallback_assets = dict(re.findall(r'(\w+):\s*"(V4-LOU-P\d+)"', fallback_source))
    manifest_source = (frontend / "src/features/story/assets/storyAssetManifest.ts").read_text(
        encoding="utf-8"
    )
    manifest_files = dict(
        re.findall(r'asset\(\s*"(V4-LOU-P\d+)"\s*,\s*"([^"]+)"', manifest_source)
    )

    # Both initial session restoration and chapter review must carry the same images.
    for suffix in ("", f"/nodes/{CHAPTER_ID}"):
        response = client.get(
            f"/api/v1/story-sessions/{session.session_id}{suffix}?language={language}"
        )
        assert response.status_code == 200, response.text
        assert "solution" not in response.text
        payload = response.json()
        chapter = payload if suffix else payload["current_chapter"]
        options = chapter["puzzle"]["options"]
        assert len(options) == len({option["id"] for option in options}) == 6
        for option in options:
            asset_id = option.get("asset_id") or fallback_assets.get(option["id"])
            assert asset_id in manifest_files, f"{option['id']} has no frontend image"
            assert (frontend / "public/story/v4" / manifest_files[asset_id]).is_file()

        by_id = {option["id"]: option for option in options}
        assert set(by_id) == set(CORRECT_PIECES) | set(DISTRACTOR_ASSETS)
        for (piece_id, asset_id), label in zip(
            DISTRACTOR_ASSETS.items(), DISTRACTOR_LABELS[language]
        ):
            assert by_id[piece_id]["asset_id"] == asset_id
            assert by_id[piece_id]["text"] == label


def test_replacement_pieces_remain_distractors_without_changing_progress_or_solution():
    story = load_story(STORY_ID)
    puzzle = chapter_by_id(story, CHAPTER_ID)["puzzle"]
    assert puzzle["solution"] == CORRECT_PIECES
    session = _session()

    for distractor in DISTRACTOR_ASSETS:
        result = apply_action(
            story,
            session,
            StoryActionRequest(
                action="answer", chapter_id=CHAPTER_ID, answer=CORRECT_PIECES[:3] + [distractor]
            ),
        )
        assert not result.accepted
        assert session.current_chapter_id == CHAPTER_ID
        assert not session.state.rewards
        assert CHAPTER_ID not in session.state.completed_chapter_ids

    solved = apply_action(
        story,
        session,
        StoryActionRequest(action="answer", chapter_id=CHAPTER_ID, answer=CORRECT_PIECES),
    )
    assert solved.accepted
    assert session.current_chapter_id == "chapter_mount_fortress"
    assert [reward.id for reward in solved.new_rewards] == ["note_petal_5"]
