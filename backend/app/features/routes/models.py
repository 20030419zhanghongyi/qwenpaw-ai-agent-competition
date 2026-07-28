"""Stable API response models for database-backed routes."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import Preference


class RouteNodeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    poi_id: str
    order: int
    suggested_stay_min: int
    note: str
    replaceable_with: list[str]


class RouteTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    theme: str
    duration_label: str
    duration_hours: float
    walk_distance_km: float
    physical_level: str
    suitable_for: list[str]
    nodes: list[RouteNodeResponse]
    description: str


class RouteMatchItemResponse(BaseModel):
    route: dict[str, Any]
    score: int
    reasons: list[str]
    selected_template: str
    candidate_pois: list[dict[str, Any]]
    applied_constraints: list[str]
    explanation: dict[str, Any]
    live_context: dict[str, Any] = Field(default_factory=dict)


class RouteMatchResponse(BaseModel):
    preference: Preference
    matches: list[RouteMatchItemResponse]


class RouteAdjustResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    selected_template: str
    instruction: str
    preference_before: Preference
    preference_after: Preference
    route: dict[str, Any]
    candidate_pois: list[dict[str, Any]]
    removed_nodes: list[dict[str, Any]]
    added_nodes: list[dict[str, Any]]
    reordered_nodes: list[dict[str, Any]]
    rationale: list[str]
    applied_constraints: list[str]
    explanation: dict[str, Any]
    source: str


class WalkPathRequest(BaseModel):
    # Theme days can exceed the old 12-stop cap (ports + dense fills).
    poi_ids: list[str] = Field(min_length=2, max_length=24)

    @field_validator("poi_ids")
    @classmethod
    def poi_ids_must_not_repeat_adjacently(cls, value: list[str]) -> list[str]:
        # Same entry/exit port is valid (e.g. 横琴 → … → 横琴). Only reject
        # consecutive duplicates, which would create a zero-length hop.
        for left, right in zip(value, value[1:]):
            if left == right:
                raise ValueError("poi_ids must not contain consecutive duplicates")
        return value


class TransitModeResponse(BaseModel):
    kind: str
    label: str


class WalkSegmentResponse(BaseModel):
    from_poi_id: str
    to_poi_id: str
    walk_m: int = Field(ge=0)
    walk_min: int = Field(ge=0)
    polyline: str
    bus_lines: list[str] = Field(default_factory=list)
    bus_from_stop: str | None = None
    bus_to_stop: str | None = None
    preferred_mode: str = "walk"
    modes: list[TransitModeResponse] = Field(default_factory=list)


class WalkPathResponse(BaseModel):
    segments: list[WalkSegmentResponse]
    total_walk_m: int = Field(ge=0)
    total_walk_min: int = Field(ge=0)
    polyline: str
