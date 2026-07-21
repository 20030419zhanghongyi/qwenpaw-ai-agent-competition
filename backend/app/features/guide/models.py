"""Structured cultural companion payloads for the guide feature.

Immersive schema is the new location-aware companion format.
Legacy ``sections`` / flat ``text`` remain for older clients and TTS fallbacks.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
