"""Deterministic, AI-free story session transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .content import chapter_by_id
from .models import StoryAction, StoryActionRequest, StorySession, StorySessionStatus


class InvalidStoryActionError(ValueError):
    pass


class StoryChapterConflictError(RuntimeError):
    pass


@dataclass
class TransitionResult:
    accepted: bool
    message: str
    hint: str | None = None
    new_clues: list[str] = field(default_factory=list)
    changed: bool = True


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _normalized_answer(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [_normalized_answer(item) for item in value]
    return value


def _require_arrival(story_session: StorySession, chapter_id: str) -> None:
    if chapter_id not in story_session.state.arrived_chapter_ids:
        raise StoryChapterConflictError("??????????")


def _advance(story: dict[str, Any], story_session: StorySession) -> None:
    chapters = sorted(story["chapters"], key=lambda item: item["order"])
    current_index = next(
        index
        for index, chapter in enumerate(chapters)
        if chapter["id"] == story_session.current_chapter_id
    )
    if current_index + 1 < len(chapters):
        story_session.current_chapter_id = chapters[current_index + 1]["id"]


def _complete_puzzle(
    story: dict[str, Any],
    story_session: StorySession,
    chapter: dict[str, Any],
    *,
    skipped: bool,
) -> list[str]:
    chapter_id = chapter["id"]
    target = (
        story_session.state.skipped_chapter_ids
        if skipped
        else story_session.state.completed_chapter_ids
    )
    _append_unique(target, chapter_id)
    reward = chapter["puzzle"].get("reward_clue")
    new_clues: list[str] = []
    if reward:
        clue_id = reward["id"]
        if clue_id not in story_session.state.clues:
            story_session.state.clues.append(clue_id)
            new_clues.append(clue_id)
    _advance(story, story_session)
    return new_clues


def _already_processed(story_session: StorySession, chapter_id: str) -> bool:
    return chapter_id in {
        *story_session.state.completed_chapter_ids,
        *story_session.state.skipped_chapter_ids,
    }


def allowed_actions(story: dict[str, Any], story_session: StorySession) -> list[StoryAction]:
    if story_session.status == StorySessionStatus.COMPLETED:
        return []
    chapter = chapter_by_id(story, story_session.current_chapter_id)
    if chapter["id"] not in story_session.state.arrived_chapter_ids:
        return [StoryAction.ARRIVE]
    optional_actions = []
    collectible = chapter.get("collectible")
    if (
        isinstance(collectible, dict)
        and collectible.get("id") not in story_session.state.collectibles
    ):
        optional_actions.append(StoryAction.COLLECT)
    if chapter["kind"] == "puzzle":
        return [StoryAction.ANSWER, StoryAction.HINT, StoryAction.SKIP, *optional_actions]
    if chapter["kind"] == "narrative":
        return [StoryAction.CONTINUE, *optional_actions]
    if chapter["kind"] == "ending":
        return [StoryAction.CHOOSE_ENDING, *optional_actions]
    raise InvalidStoryActionError(f"Unsupported chapter kind: {chapter['kind']}")


def apply_action(
    story: dict[str, Any],
    story_session: StorySession,
    request: StoryActionRequest,
) -> TransitionResult:
    """Apply one idempotent action to a detached session domain object."""
    if story_session.status == StorySessionStatus.COMPLETED:
        if (
            request.action == StoryAction.CHOOSE_ENDING
            and request.choice_id == story_session.state.ending_id
        ):
            return TransitionResult(True, "???????", changed=False)
        raise StoryChapterConflictError("??????????????")

    if request.chapter_id != story_session.current_chapter_id:
        if _already_processed(story_session, request.chapter_id):
            return TransitionResult(True, "???????", changed=False)
        raise StoryChapterConflictError(
            f"????? {story_session.current_chapter_id}????? {request.chapter_id}"
        )

    chapter = chapter_by_id(story, request.chapter_id)
    if (
        request.action == StoryAction.ARRIVE
        and request.chapter_id in story_session.state.arrived_chapter_ids
    ):
        return TransitionResult(True, "??????????", changed=False)
    if (
        request.action == StoryAction.COLLECT
        and request.collectible_id in story_session.state.collectibles
    ):
        return TransitionResult(True, "?????????", changed=False)
    permitted = allowed_actions(story, story_session)
    if request.action not in permitted:
        raise InvalidStoryActionError(
            f"?? {request.chapter_id} ??????? {request.action.value}"
        )

    if request.action == StoryAction.ARRIVE:
        _append_unique(story_session.state.arrived_chapter_ids, request.chapter_id)
        return TransitionResult(True, "?????????")

    _require_arrival(story_session, request.chapter_id)

    if request.action == StoryAction.COLLECT:
        collectible = chapter.get("collectible")
        if not isinstance(collectible, dict):
            raise InvalidStoryActionError("??????????????")
        collectible_id = collectible.get("id")
        if request.collectible_id != collectible_id:
            raise InvalidStoryActionError("collectible_id ?????????????")
        story_session.state.collectibles.append(collectible_id)
        return TransitionResult(True, collectible.get("collect_text", "???????"))

    if request.action == StoryAction.HINT:
        puzzle = chapter["puzzle"]
        hints = puzzle.get("hints") or []
        if not hints:
            raise InvalidStoryActionError("??????????")
        count = story_session.state.hint_counts.get(request.chapter_id, 0)
        hint = hints[min(count, len(hints) - 1)]
        story_session.state.hint_counts[request.chapter_id] = count + 1
        _append_unique(story_session.state.hinted_chapter_ids, request.chapter_id)
        return TransitionResult(True, "?????", hint=hint)

    if request.action == StoryAction.ANSWER:
        if request.answer is None:
            raise InvalidStoryActionError("????? answer ????")
        puzzle = chapter["puzzle"]
        if _normalized_answer(request.answer) != _normalized_answer(puzzle["solution"]):
            attempts = story_session.state.attempts.get(request.chapter_id, 0) + 1
            story_session.state.attempts[request.chapter_id] = attempts
            return TransitionResult(False, "??????????????????")
        new_clues = _complete_puzzle(story, story_session, chapter, skipped=False)
        return TransitionResult(
            True,
            puzzle["explanation"],
            new_clues=new_clues,
        )

    if request.action == StoryAction.SKIP:
        puzzle = chapter["puzzle"]
        new_clues = _complete_puzzle(story, story_session, chapter, skipped=True)
        return TransitionResult(True, puzzle["skip_text"], new_clues=new_clues)

    if request.action == StoryAction.CONTINUE:
        _append_unique(story_session.state.completed_chapter_ids, request.chapter_id)
        _advance(story, story_session)
        return TransitionResult(True, "?????")

    if request.action == StoryAction.CHOOSE_ENDING:
        if not request.choice_id:
            raise InvalidStoryActionError("????? choice_id ????")
        ending_ids = {ending["id"] for ending in story.get("endings", [])}
        if request.choice_id not in ending_ids:
            raise InvalidStoryActionError(f"??????: {request.choice_id}")
        story_session.state.choices[request.chapter_id] = request.choice_id
        story_session.state.ending_id = request.choice_id
        for side_quest in story.get("side_quests", []):
            required = set(side_quest.get("required_collectible_ids", []))
            if required and required.issubset(story_session.state.collectibles):
                bonus_id = side_quest.get("bonus_ending", {}).get("id")
                if bonus_id:
                    _append_unique(story_session.state.unlocked_bonus_ids, bonus_id)
        _append_unique(story_session.state.completed_chapter_ids, request.chapter_id)
        story_session.status = StorySessionStatus.COMPLETED
        story_session.completed_at = datetime.now(timezone.utc)
        return TransitionResult(True, "????????????")

    raise InvalidStoryActionError(f"Unsupported action: {request.action.value}")
