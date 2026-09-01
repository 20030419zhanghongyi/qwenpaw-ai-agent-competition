"""StoryWalk context adapter for the shared Guide question-answering pipeline."""

from app.features.stories.models import StorySessionStatus
from app.features.stories.service import story_service

from .models import GuideStoryReference, StoryGuideContext, StoryGuideKnowledgeCard


def resolve_story_guide_context(
    reference: GuideStoryReference, user_id: str, *, language: str
) -> StoryGuideContext:
    """Reuse story ownership/version/unlock checks without exposing private puzzle data."""
    session = story_service.get_session(reference.session_id, user_id, language=language)
    chapter_id = reference.chapter_id or session.current_chapter_id
    chapter = story_service.get_chapter(
        reference.session_id, user_id, chapter_id, language=language
    )
    story = story_service.get_story(session.story_id, language=language)
    context = chapter.get("agent_context") or {}
    completed = session.status == StorySessionStatus.COMPLETED
    unlocked_ids = {
        session.current_chapter_id,
        *session.state.completed_chapter_ids,
        *session.state.skipped_chapter_ids,
    }
    return StoryGuideContext(
        story_id=session.story_id,
        story_title=story["title"],
        story_summary=story.get("summary", ""),
        story_summaries=story_service.get_story_summaries(language=language),
        chapter_id=chapter_id,
        chapter_title=chapter["title"],
        persona=context.get("persona") or "阿莲",
        poi_id=chapter.get("poi_id"),
        poi_name=context.get("poi_name") or chapter.get("location_name") or story["title"],
        chapter_goal=context.get("chapter_goal", ""),
        scene=chapter.get("scene", ""),
        dialogue=[
            f"{line.get('speaker', '')}: {line['text']}"
            for line in chapter.get("dialogue", [])
            if line.get("text")
        ],
        known_facts=context.get("known_facts", []),
        fiction_boundaries=context.get("fiction_boundaries", []),
        do_not_reveal=context.get("do_not_reveal", []),
        knowledge_cards=[
            StoryGuideKnowledgeCard.model_validate(card)
            for card in chapter.get("knowledge_cards", [])
        ],
        unlocked_chapters=[
            node["title"] for node in story.get("nodes", []) if node["id"] in unlocked_ids
        ],
        story_completed=completed,
        # Do not send ending_reflection or the user's other private session state to QwenPaw.
        ending_text=str((session.ending or {}).get("text") or "") if completed else "",
    )


def story_guide_fallback(context: StoryGuideContext, *, language: str) -> str:
    """Keep the chapter usable when the model is disabled or unavailable."""
    intro, reminder = {
        "zh-CN": (
            "阿莲的即时问答暂时不可用，我们先看看「{chapter}」已经公开的资料：",
            "这些是本章预置资料，并非对刚才问题的新回答；你可以稍后重试，"
            "或继续查看知识卡、使用提示和推进故事。",
        ),
        "zh-TW": (
            "阿蓮的即時問答暫時不可用，我們先看看「{chapter}」已公開的資料：",
            "這些是本章預設資料，並非對剛才問題的新回答；你可稍後重試，"
            "或繼續查看知識卡、使用提示及推進故事。",
        ),
        "en": (
            'A Lin’s live answers are temporarily unavailable. '
            'Here are the published notes for “{chapter}”: ',
            "These are this chapter’s preset notes, not a new answer to your question. "
            "Try again later, read the knowledge cards, use a hint, or continue the story.",
        ),
        "pt": (
            'As respostas de A Lin estão temporariamente indisponíveis. Eis as notas de «{chapter}»: ',
            "Estas são as notas do capítulo, não uma nova resposta à sua pergunta. "
            "Tente mais tarde, consulte os cartões, peça uma pista ou continue a história.",
        ),
    }.get(language, ("{chapter}", ""))
    notes = [
        f"{card.title}: {card.text} ({card.source_label or card.kind})"
        for card in context.knowledge_cards[:2]
    ] or context.known_facts[:2]
    return "\n\n".join([intro.format(chapter=context.chapter_title), *notes, reminder])
