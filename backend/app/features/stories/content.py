"""Load curated story content and keep puzzle solutions server-side."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


STORY_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "stories"


class StoryNotFoundError(LookupError):
    pass


class StoryContentError(ValueError):
    pass


def load_story(story_id: str) -> dict[str, Any]:
    """Load and minimally validate a private story definition."""
    if not story_id or any(part in story_id for part in ("/", "\\", "..")):
        raise StoryNotFoundError(f"Story not found: {story_id}")
    path = STORY_DATA_DIR / f"{story_id}.json"
    if not path.is_file():
        raise StoryNotFoundError(f"Story not found: {story_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("id") != story_id:
        raise StoryContentError(f"Story id does not match file name: {story_id}")
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise StoryContentError(f"Story has no chapters: {story_id}")
    chapter_ids = [chapter.get("id") for chapter in chapters]
    if any(not chapter_id for chapter_id in chapter_ids) or len(set(chapter_ids)) != len(
        chapter_ids
    ):
        raise StoryContentError(f"Story has missing or duplicate chapter ids: {story_id}")
    orders = [chapter.get("order") for chapter in chapters]
    if any(not isinstance(order, int) for order in orders) or len(set(orders)) != len(orders):
        raise StoryContentError(f"Story has missing or duplicate chapter orders: {story_id}")
    supported_kinds = {"puzzle", "narrative", "ending"}
    for chapter in chapters:
        if chapter.get("kind") not in supported_kinds:
            raise StoryContentError(f"Story has unsupported chapter kind: {chapter.get('kind')}")
        if not chapter.get("poi_id"):
            raise StoryContentError(f"Story chapter has no poi_id: {chapter.get('id')}")
        if chapter["kind"] == "puzzle":
            puzzle = chapter.get("puzzle")
            if not isinstance(puzzle, dict) or "solution" not in puzzle:
                raise StoryContentError(
                    f"Puzzle chapter has no private solution: {chapter.get('id')}"
                )
    return payload


def public_story(story: dict[str, Any]) -> dict[str, Any]:
    """Return client-safe content without solutions or private ending rules."""
    public = deepcopy(story)
    for chapter in public.get("chapters", []):
        puzzle = chapter.get("puzzle")
        if isinstance(puzzle, dict):
            puzzle.pop("solution", None)
    for ending in public.get("endings", []):
        ending.pop("condition", None)
    return public


def story_overview(story: dict[str, Any]) -> dict[str, Any]:
    """Return spoiler-light metadata for the story landing page."""
    overview = {
        key: deepcopy(value) for key, value in story.items() if key not in {"chapters", "endings"}
    }
    overview["chapters"] = [
        {
            key: deepcopy(chapter[key])
            for key in ("id", "order", "kind", "title", "story_time", "poi_id")
        }
        for chapter in story["chapters"]
    ]
    overview["endings"] = [
        {key: deepcopy(ending[key]) for key in ("id", "title", "choice_text")}
        for ending in story.get("endings", [])
    ]
    return overview


def chapter_by_id(story: dict[str, Any], chapter_id: str) -> dict[str, Any]:
    for chapter in story["chapters"]:
        if chapter["id"] == chapter_id:
            return chapter
    raise StoryContentError(f"Chapter not found in story: {chapter_id}")


def public_chapter(chapter: dict[str, Any]) -> dict[str, Any]:
    safe = deepcopy(chapter)
    puzzle = safe.get("puzzle")
    if isinstance(puzzle, dict):
        puzzle.pop("solution", None)
    return safe
