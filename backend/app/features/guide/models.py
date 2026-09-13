"""Structured cultural companion payloads for the guide feature.

Immersive schema is the new location-aware companion format.
Legacy ``sections`` / flat ``text`` remain for older clients and TTS fallbacks.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.guardrails.runtime import sanitize_untrusted_text


class GuideStoryReference(BaseModel):
    """Resolve story context on the server, never accept client-authored plot facts."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=128)
    chapter_id: str | None = Field(default=None, min_length=1, max_length=128)


class GuideConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        value = sanitize_untrusted_text(value, max_length=2000)
        if not value:
            raise ValueError("message must not be blank")
        return value


class StoryGuideKnowledgeCard(BaseModel):
    kind: str
    title: str
    text: str
    source_label: str = ""


class StoryGuideContext(BaseModel):
    """Allowlisted, unlocked story content; no puzzle, reward or private reflection."""

    story_id: str
    story_title: str
    story_summary: str
    story_summaries: list[dict[str, str]] = Field(default_factory=list)
    chapter_id: str
    chapter_title: str
    persona: str
    poi_id: str | None = None
    poi_name: str
    chapter_goal: str = ""
    scene: str = ""
    dialogue: list[str] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    fiction_boundaries: list[str] = Field(default_factory=list)
    do_not_reveal: list[str] = Field(default_factory=list)
    knowledge_cards: list[StoryGuideKnowledgeCard] = Field(default_factory=list)
    unlocked_chapters: list[str] = Field(default_factory=list)
    story_completed: bool = False
    ending_text: str = ""


class ObservationItem(BaseModel):
    observation: str = ""
    explanation: str = ""


class NextExploration(BaseModel):
    location: str = ""
    distance: str = ""
    walk_time: str = ""
    reason: str = ""


class ImmersiveGuide(BaseModel):
    """Location-aware cultural companion (macau-guide structured output)."""

    title: str = ""
    subtitle: str = ""
    hook: str = ""
    why_it_matters: str = ""
    historical_story: str = ""
    things_to_observe: list[ObservationItem] = Field(default_factory=list)
    local_story: str = ""
    interactive_suggestion: str = ""
    next_exploration: NextExploration = Field(default_factory=NextExploration)
    audio_script: str = ""

    def to_public_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "hook": self.hook,
            "why_it_matters": self.why_it_matters,
            "historical_story": self.historical_story,
            "things_to_observe": [
                {"observation": o.observation, "explanation": o.explanation}
                for o in self.things_to_observe
                if (o.observation or "").strip()
            ],
            "local_story": self.local_story,
            "interactive_suggestion": self.interactive_suggestion,
            "next_exploration": {
                "location": self.next_exploration.location,
                "distance": self.next_exploration.distance,
                "walk_time": self.next_exploration.walk_time,
                "reason": self.next_exploration.reason,
            },
            "audio_script": self.audio_script,
        }
