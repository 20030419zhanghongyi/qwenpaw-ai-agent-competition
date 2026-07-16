"""AMap v5 walking-direction adapter for ordered POI sequences."""

from __future__ import annotations

import math
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.pois.repository import PoiRepository

AMAP_WALKING_URL = "https://restapi.amap.com/v5/direction/walking"


class WalkingPathError(RuntimeError):
    pass


class AmapWalkingClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.amap_web_service_key

    def segment(self, origin: tuple[float, float], destination: tuple[float, float]) -> dict[str, Any]:
        if not self._api_key:
            raise WalkingPathError("AMap walking service is not configured")
        params = {
            "key": self._api_key,
            "origin": f"{origin[0]:.6f},{origin[1]:.6f}",
            "destination": f"{destination[0]:.6f},{destination[1]:.6f}",
            "output": "json",
        }
        try:
            response = httpx.get(AMAP_WALKING_URL, params=params, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WalkingPathError("AMap walking service is unavailable") from exc
        if str(payload.get("status")) != "1":
            raise WalkingPathError("AMap walking service rejected the route request")
        paths = (payload.get("route") or {}).get("paths") or []
        if not paths:
            raise WalkingPathError("AMap returned no walking path")
        return paths[0]


def build_walk_path(poi_ids: list[str], database: Session, *, client: AmapWalkingClient | None = None) -> dict:
    pois = PoiRepository(database).get_by_ids(poi_ids)
    missing = [poi_id for poi_id in poi_ids if poi_id not in pois]
    if missing:
        raise KeyError(", ".join(missing))

    client = client or AmapWalkingClient()
    segments: list[dict] = []
    total_distance = 0
    total_duration = 0
    polylines: list[str] = []
    for from_id, to_id in zip(poi_ids, poi_ids[1:]):
        origin, destination = pois[from_id], pois[to_id]
        path = client.segment((origin.longitude, origin.latitude), (destination.longitude, destination.latitude))
        distance = int(float(path.get("distance") or 0))
        duration = int(float(path.get("duration") or 0))
        steps = path.get("steps") or []
        polyline = ";".join(str(step.get("polyline") or "") for step in steps if step.get("polyline"))
        total_distance += distance
        total_duration += duration
        if polyline:
            polylines.append(polyline)
        segments.append(
            {
                "from_poi_id": from_id,
                "to_poi_id": to_id,
                "walk_m": distance,
                "walk_min": math.ceil(duration / 60),
                "polyline": polyline,
            }
        )
    return {
        "segments": segments,
        "total_walk_m": total_distance,
        "total_walk_min": math.ceil(total_duration / 60),
        "polyline": ";".join(polylines),
    }
