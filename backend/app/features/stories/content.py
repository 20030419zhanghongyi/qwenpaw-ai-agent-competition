"""Load curated story content and keep puzzle solutions server-side."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


STORY_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "stories"
SUPPORTED_STORY_LANGUAGES = frozenset({"zh-CN", "zh-TW", "en", "pt"})
_STRUCTURAL_FIELDS = frozenset(
    {
        "id",
        "version",
        "route_id",
        "poi_id",
        "order",
        "kind",
        "type",
        "solution",
        "condition",
        "action",
        "choice_id",
    }
)


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
    nodes = story_nodes(payload)
    if not nodes:
        raise StoryContentError(f"Story has no nodes or chapters: {story_id}")
    chapter_ids = [chapter.get("id") for chapter in nodes]
    if any(not chapter_id for chapter_id in chapter_ids) or len(set(chapter_ids)) != len(
        chapter_ids
    ):
        raise StoryContentError(f"Story has missing or duplicate chapter ids: {story_id}")
    return payload


def normalize_story_language(language: str | None) -> str:
    """Return a supported StoryWalk locale, falling back to the source language.

    Story packages are authored in Simplified Chinese.  API callers can request
    one of the four product locales; an invalid or omitted value must never make
    a persisted story session unreadable.
    """
    return language if language in SUPPORTED_STORY_LANGUAGES else "zh-CN"


def _load_locale_overlay(story_id: str, language: str) -> dict[str, Any]:
    """Load an optional, content-reviewable locale overlay for one story.

    Keeping translations in ``<story-id>.locales.json`` avoids duplicating the
    private puzzle solutions and structural IDs in every language.  The overlay
    contains only display text keyed by stable node / ending identifiers.
    """
    if language == "zh-CN":
        return {}
    path = STORY_DATA_DIR / f"{story_id}.locales.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    overlay = payload.get(language)
    return overlay if isinstance(overlay, dict) else {}


def _merge_display_text(source: Any, overlay: Any, *, field: str | None = None) -> Any:
    """Deep-merge an overlay while retaining source-only puzzle mechanics.

    Locale files are allowed to replace strings and add translated nested fields,
    but cannot remove IDs, answer schemas, or other source data required by the
    deterministic story engine.
    """
    if field in _STRUCTURAL_FIELDS:
        return deepcopy(source)
    if isinstance(source, dict) and isinstance(overlay, dict):
        merged = deepcopy(source)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = _merge_display_text(merged[key], value, field=key)
            else:
                merged[key] = deepcopy(value)
        return merged
    if isinstance(source, list) and isinstance(overlay, list):
        # Arrays in the public content are ordered. Locale overlays therefore
        # use the same item order and only replace corresponding text fields.
        return [
            _merge_display_text(item, overlay[index]) if index < len(overlay) else deepcopy(item)
            for index, item in enumerate(source)
        ]
    return deepcopy(overlay) if isinstance(overlay, str) else deepcopy(source)


def localize_story(story: dict[str, Any], language: str | None) -> dict[str, Any]:
    """Return localized display content without changing the canonical story."""
    locale = normalize_story_language(language)
    overlay = _load_locale_overlay(str(story.get("id") or ""), locale)
    return _merge_display_text(story, overlay)


def story_nodes(story: dict[str, Any]) -> list[dict[str, Any]]:
    """Return v3 nodes, or legacy chapters for packages not yet migrated."""
    nodes = story.get("nodes")
    if isinstance(nodes, list):
        return nodes
    chapters = story.get("chapters")
    return chapters if isinstance(chapters, list) else []


def public_story(story: dict[str, Any]) -> dict[str, Any]:
    """Return client-safe content without solutions or private ending rules."""
    public = deepcopy(story)
    for chapter in story_nodes(public):
        puzzle = chapter.get("puzzle")
        if isinstance(puzzle, dict):
            puzzle.pop("solution", None)
    for ending in public.get("endings", []):
        ending.pop("condition", None)
    return public


def story_overview(story: dict[str, Any]) -> dict[str, Any]:
    """Return spoiler-light metadata for the story landing page."""
    overview = {
        key: deepcopy(value)
        for key, value in story.items()
        if key not in {"nodes", "chapters", "endings"}
    }
    overview["nodes"] = [
        {
            key: deepcopy(chapter[key])
            for key in (
                "id",
                "order",
                "kind",
                "title",
                "story_time",
                "location_name",
                "poi_id",
            )
            if key in chapter
        }
        for chapter in story_nodes(story)
    ]
    overview["endings"] = [
        {
            key: deepcopy(ending[key])
            for key in ("id", "title", "choice_text")
        }
        for ending in story.get("endings", [])
    ]
    return overview


def chapter_by_id(story: dict[str, Any], chapter_id: str) -> dict[str, Any]:
    for chapter in story_nodes(story):
        if chapter["id"] == chapter_id:
            return chapter
    raise StoryContentError(f"Chapter not found in story: {chapter_id}")


def public_chapter(chapter: dict[str, Any]) -> dict[str, Any]:
    safe = deepcopy(chapter)
    puzzle = safe.get("puzzle")
    if isinstance(puzzle, dict):
        puzzle.pop("solution", None)
    return safe
