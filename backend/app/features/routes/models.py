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
    poi_ids: list[str] = Field(min_length=2, max_length=12)

    @field_validator("poi_ids")
    @classmethod
    def poi_ids_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("poi_ids must not contain duplicates")
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
    modes: list[TransitModeResponse] = Field(default_factory=list)


class WalkPathResponse(BaseModel):
    segments: list[WalkSegmentResponse]
    total_walk_m: int = Field(ge=0)
    total_walk_min: int = Field(ge=0)
    polyline: str
