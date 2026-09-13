"""Deterministic, AI-free story session transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any

from .content import chapter_by_id, story_nodes
from .models import StoryAction, StoryActionRequest, StoryReward, StorySession, StorySessionStatus


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
    new_rewards: list[StoryReward] = field(default_factory=list)
    message_key: str | None = None
    changed: bool = True
    # Display references survive chapter advancement; never localize puzzle rules.
    chapter_id: str | None = None
    hint_index: int | None = None


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _normalized_answer(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        normalized = [_normalized_answer(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    if isinstance(value, dict):
        return {
            key: _normalized_answer(value[key])
            for key in sorted(value)
        }
    return value


def _require_arrival(story_session: StorySession, chapter_id: str) -> None:
    if chapter_id not in story_session.state.arrived_chapter_ids:
        raise StoryChapterConflictError("请先确认到达当前地点")


def _advance(story: dict[str, Any], story_session: StorySession) -> None:
    chapters = sorted(story_nodes(story), key=lambda item: item["order"])
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
) -> tuple[list[str], list[StoryReward]]:
    chapter_id = chapter["id"]
    target = (
        story_session.state.skipped_chapter_ids
        if skipped
        else story_session.state.completed_chapter_ids
    )
    _append_unique(target, chapter_id)
    reward = chapter["puzzle"].get("reward")
    if reward is None:
        reward = chapter["puzzle"].get("reward_clue")
    new_clues, new_rewards = _award_reward(story_session, reward)
    _advance(story, story_session)
    return new_clues, new_rewards


def _award_reward(
    story_session: StorySession, reward: dict[str, Any] | None
) -> tuple[list[str], list[StoryReward]]:
    if not reward:
        return [], []
    normalized = StoryReward.model_validate(
        {"kind": "stamp", **reward} if "kind" not in reward else reward
    )
    new_rewards: list[StoryReward] = []
    new_clues: list[str] = []
    if normalized.id not in {item.id for item in story_session.state.rewards}:
        story_session.state.rewards.append(normalized)
        new_rewards.append(normalized)
    if normalized.id not in story_session.state.clues:
        story_session.state.clues.append(normalized.id)
        new_clues.append(normalized.id)
    return new_clues, new_rewards


def _already_processed(story_session: StorySession, chapter_id: str) -> bool:
    return chapter_id in {
        *story_session.state.completed_chapter_ids,
        *story_session.state.skipped_chapter_ids,
    }


def allowed_actions(
    story: dict[str, Any], story_session: StorySession
) -> list[StoryAction]:
    if story_session.status == StorySessionStatus.COMPLETED:
        return []
    chapter = chapter_by_id(story, story_session.current_chapter_id)
    if chapter.get("poi_id") and chapter["id"] not in story_session.state.arrived_chapter_ids:
        return [StoryAction.ARRIVE]
    if chapter["kind"] == "puzzle":
        return [StoryAction.ANSWER, StoryAction.HINT, StoryAction.SKIP]
    if chapter["kind"] in {"prologue", "narrative", "transition"}:
        return [StoryAction.CONTINUE]
    if chapter["kind"] == "ending":
        return [StoryAction.CHOOSE_ENDING]
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
            return TransitionResult(
                True, "该结局已经保存", message_key="ending_already_saved", changed=False
            )
        raise StoryChapterConflictError("故事已经完成，不能再修改进度")

    if request.chapter_id != story_session.current_chapter_id:
        if _already_processed(story_session, request.chapter_id):
            return TransitionResult(
                True, "该章节已经处理", message_key="chapter_already_processed", changed=False
            )
        raise StoryChapterConflictError(
            f"当前章节是 {story_session.current_chapter_id}，不能操作 {request.chapter_id}"
        )

    chapter = chapter_by_id(story, request.chapter_id)
    if (
        request.action == StoryAction.ARRIVE
        and request.chapter_id in story_session.state.arrived_chapter_ids
    ):
        return TransitionResult(
            True,
            "已经确认到达当前地点",
            message_key="arrival_confirmed",
            changed=False,
        )
    permitted = allowed_actions(story, story_session)
    if request.action not in permitted:
        raise InvalidStoryActionError(
            f"章节 {request.chapter_id} 当前不允许操作 {request.action.value}"
        )

    if request.action == StoryAction.ARRIVE:
        _append_unique(story_session.state.arrived_chapter_ids, request.chapter_id)
        return TransitionResult(
            True,
            "已到达当前剧情地点",
            message_key="arrival_confirmed",
        )

    if chapter.get("poi_id"):
        _require_arrival(story_session, request.chapter_id)

    if request.action == StoryAction.HINT:
        puzzle = chapter["puzzle"]
        hints = puzzle.get("hints") or []
        if not hints:
            raise InvalidStoryActionError("当前谜题没有可用提示")
        count = story_session.state.hint_counts.get(request.chapter_id, 0)
        hint_index = min(count, len(hints) - 1)
        hint = hints[hint_index]
        story_session.state.hint_counts[request.chapter_id] = count + 1
        _append_unique(story_session.state.hinted_chapter_ids, request.chapter_id)
        return TransitionResult(
            True,
            "已提供提示",
            hint=hint,
            message_key="hint_provided",
            chapter_id=request.chapter_id,
            hint_index=hint_index,
        )

    if request.action == StoryAction.ANSWER:
        if request.answer is None:
            raise InvalidStoryActionError("提交答案时 answer 不能为空")
        puzzle = chapter["puzzle"]
        if _normalized_answer(request.answer) != _normalized_answer(puzzle["solution"]):
            attempts = story_session.state.attempts.get(request.chapter_id, 0) + 1
            story_session.state.attempts[request.chapter_id] = attempts
            return TransitionResult(
                False,
                "答案不正确，可以重试、查看提示或跳过",
                message_key="incorrect_answer",
            )
        new_clues, new_rewards = _complete_puzzle(story, story_session, chapter, skipped=False)
        return TransitionResult(
            True,
            puzzle["explanation"],
            new_clues=new_clues,
            new_rewards=new_rewards,
            message_key="puzzle_solved",
            chapter_id=request.chapter_id,
        )

    if request.action == StoryAction.SKIP:
        puzzle = chapter["puzzle"]
        new_clues, new_rewards = _complete_puzzle(story, story_session, chapter, skipped=True)
        return TransitionResult(
            True,
            puzzle["skip_text"],
            new_clues=new_clues,
            new_rewards=new_rewards,
            message_key="puzzle_skipped",
            chapter_id=request.chapter_id,
        )

    if request.action == StoryAction.CONTINUE:
        _append_unique(story_session.state.completed_chapter_ids, request.chapter_id)
        new_clues, new_rewards = _award_reward(story_session, chapter.get("reward"))
        _advance(story, story_session)
        return TransitionResult(
            True,
            "剧情已继续",
            new_clues=new_clues,
            new_rewards=new_rewards,
            message_key="story_continued",
        )

    if request.action == StoryAction.CHOOSE_ENDING:
        if not request.choice_id:
            raise InvalidStoryActionError("选择结局时 choice_id 不能为空")
        ending_ids = {ending["id"] for ending in story.get("endings", [])}
        if request.choice_id not in ending_ids:
            raise InvalidStoryActionError(f"未知结局选项: {request.choice_id}")
        story_session.state.choices[request.chapter_id] = request.choice_id
        story_session.state.ending_id = request.choice_id
        story_session.state.ending_reflection = request.reflection
        _append_unique(story_session.state.completed_chapter_ids, request.chapter_id)
        story_session.status = StorySessionStatus.COMPLETED
        story_session.completed_at = datetime.now(timezone.utc)
        selected_ending = next(
            ending
            for ending in story.get("endings", [])
            if ending["id"] == request.choice_id
        )
        new_clues: list[str] = []
        new_rewards: list[StoryReward] = []
        for reward in selected_ending.get("rewards", []):
            clues, rewards = _award_reward(story_session, reward)
            new_clues.extend(clues)
            new_rewards.extend(rewards)
        return TransitionResult(
            True,
            "今日补记已保存，故事完成",
            new_clues=new_clues,
            new_rewards=new_rewards,
            message_key="story_completed",
        )

    raise InvalidStoryActionError(f"Unsupported action: {request.action.value}")
