"""AMap v5 walking + transit adapters for ordered POI sequences."""

from __future__ import annotations

import math
import re
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.pois.repository import PoiRepository

AMAP_WALKING_URL = "https://restapi.amap.com/v5/direction/walking"
AMAP_TRANSIT_URL = "https://restapi.amap.com/v5/direction/transit/integrated"
# AMap citycode for Macau SAR — "澳门" is rejected by v5 as INVALID_PARAMS.
MACAU_CITYCODE = "1852"
# Hengqin / Zhuhai side sometimes needed for port-adjacent transit lookups.
ZHUHAI_CITYCODE = "0756"
# Skip bus suggestions when the walk is already this short.
MIN_WALK_M_FOR_TRANSIT = 350
# Prefer bus as the primary mode when walking would take longer than this.
PREFER_BUS_WALK_MIN = 15
# Drop only extreme detours (Macau bus routes are often not shortest-path).
MAX_TRANSIT_WALK_RATIO = 8.0
# Shown when AMap returns no line but the hop is too long to walk.
FALLBACK_BUS_LABEL = "建议乘巴士（勿步行）"


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
            # AMap v5 returns duration and step polylines only when explicitly requested.
            "show_fields": "cost,polyline",
            "output": "json",
        }
        last_error: Exception | None = None
        # One retry absorbs transient AMap QPS / soft rejects.
        for attempt in range(2):
            try:
                response = httpx.get(AMAP_WALKING_URL, params=params, timeout=10.0)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = WalkingPathError("AMap walking service is unavailable")
                last_error.__cause__ = exc
                time.sleep(0.25)
                continue
            if str(payload.get("status")) != "1":
                last_error = WalkingPathError("AMap walking service rejected the route request")
                time.sleep(0.35)
                continue
            paths = (payload.get("route") or {}).get("paths") or []
            if not paths:
                last_error = WalkingPathError("AMap returned no walking path")
                time.sleep(0.25)
                continue
            return paths[0]
        assert last_error is not None
        raise last_error

    def transit_options(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        city: str = MACAU_CITYCODE,
        city2: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return transit plans; empty list on soft failure (keeps walk-path usable)."""
        if not self._api_key:
            return []
        params = {
            "key": self._api_key,
            "origin": f"{origin[0]:.6f},{origin[1]:.6f}",
            "destination": f"{destination[0]:.6f},{destination[1]:.6f}",
            "city1": city,
            "city2": city2 or city,
            "AlternativeRoute": "3",
            "strategy": "0",
            "output": "json",
            "show_fields": "cost",
        }
        try:
            response = httpx.get(AMAP_TRANSIT_URL, params=params, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        if str(payload.get("status")) != "1":
            return []
        return list((payload.get("route") or {}).get("transits") or [])

    def transit_options_resilient(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> list[dict[str, Any]]:
        """Try Macau-only, then Macau↔Zhuhai pairs (helps 横琴口岸 long hops)."""
        attempts = (
            (MACAU_CITYCODE, MACAU_CITYCODE),
            (MACAU_CITYCODE, ZHUHAI_CITYCODE),
            (ZHUHAI_CITYCODE, MACAU_CITYCODE),
        )
        for city1, city2 in attempts:
            plans = self.transit_options(origin, destination, city=city1, city2=city2)
            if plans:
                return plans
        return []


def _haversine_m(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    """Great-circle distance in meters (lon, lat) → (lon, lat)."""
    lon1, lat1 = origin
    lon2, lat2 = destination
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _estimate_walk_segment(
    origin: tuple[float, float], destination: tuple[float, float]
) -> tuple[int, int]:
    """Fallback (distance_m, duration_s) when AMap walking fails — ~80 m/min pace."""
    distance = max(1, int(round(_haversine_m(origin, destination))))
    duration = max(60, int(round(distance / 80 * 60)))
    return distance, duration


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
    # Sequential AMap calls — parallel bursts trip free-tier QPS and 503 the whole path.
    for from_id, to_id in zip(poi_ids, poi_ids[1:]):
        origin, destination = pois[from_id], pois[to_id]
        origin_ll = (origin.longitude, origin.latitude)
        dest_ll = (destination.longitude, destination.latitude)
        # Soft-fail per hop: one bad walking call must not 503 the whole itinerary
        # (FE would otherwise keep the generic “建议乘巴士” haversine chip).
        try:
            path = client.segment(origin_ll, dest_ll)
            distance = int(float(path.get("distance") or 0))
            cost = path.get("cost") or {}
            duration = int(float(cost.get("duration") or path.get("duration") or 0))
            steps = path.get("steps") or []
            polyline = ";".join(
                str(step.get("polyline") or "") for step in steps if step.get("polyline")
            )
        except WalkingPathError:
            distance, duration = _estimate_walk_segment(origin_ll, dest_ll)
            polyline = ""
        total_distance += distance
        total_duration += duration
        if polyline:
            polylines.append(polyline)

        walk_min = math.ceil(duration / 60) if duration else max(1, math.ceil(distance / 80))
        # Long hops: always ask transit (even if slightly under the short-walk meter gate).
        bus_info = _bus_info_for_segment(
            client,
            origin_ll,
            dest_ll,
            walk_m=distance,
            force=walk_min >= PREFER_BUS_WALK_MIN,
        )
        bus_lines = list(bus_info["bus_lines"])
        # AMap often returns nothing for 横琴口岸 → peninsula; still must not look walk-only.
        if walk_min >= PREFER_BUS_WALK_MIN and not bus_lines:
            bus_lines = [FALLBACK_BUS_LABEL]
            bus_info = {
                **bus_info,
                "bus_lines": bus_lines,
                "bus_from_stop": bus_info.get("bus_from_stop"),
                "bus_to_stop": bus_info.get("bus_to_stop"),
            }
        prefer_bus = walk_min >= PREFER_BUS_WALK_MIN and bool(bus_lines)
        modes: list[dict[str, str]] = []
        if prefer_bus:
            for line in bus_lines:
                modes.append({"kind": "bus", "label": line})
            modes.append({"kind": "walk", "label": f"或步行约 {walk_min} 分钟（不推荐）"})
        else:
            modes.append({"kind": "walk", "label": "步行"})
            for line in bus_lines:
                modes.append({"kind": "bus", "label": line})

        segments.append(
            {
                "from_poi_id": from_id,
                "to_poi_id": to_id,
                "walk_m": distance,
                "walk_min": walk_min,
                "polyline": polyline,
                "bus_lines": bus_lines,
                "bus_from_stop": bus_info["bus_from_stop"],
                "bus_to_stop": bus_info["bus_to_stop"],
                "preferred_mode": "bus" if prefer_bus else "walk",
                "modes": modes,
            }
        )
    return {
        "segments": segments,
        "total_walk_m": total_distance,
        "total_walk_min": math.ceil(total_duration / 60) if total_duration else max(1, math.ceil(total_distance / 80)),
        "polyline": ";".join(polylines),
    }


def _bus_info_for_segment(
    client: AmapWalkingClient,
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    walk_m: int,
    force: bool = False,
) -> dict[str, Any]:
    empty = {"bus_lines": [], "bus_from_stop": None, "bus_to_stop": None}
    if not force and walk_m < MIN_WALK_M_FOR_TRANSIT:
        return empty
    transit_fn = getattr(client, "transit_options_resilient", None) or getattr(
        client, "transit_options", None
    )
    if not callable(transit_fn):
        return empty
    plans = transit_fn(origin, destination) or []
    lines: list[str] = []
    seen: set[str] = set()
    from_stop: str | None = None
    to_stop: str | None = None
    for plan in plans:
        plan_distance = int(float(plan.get("distance") or 0))
        # When forcing long-hop transit, do not reject plans for being longer than walk.
        if (
            not force
            and walk_m > 0
            and plan_distance > walk_m * MAX_TRANSIT_WALK_RATIO
        ):
            continue
        rides = _extract_bus_rides(plan)
        if not rides:
            continue
        if from_stop is None:
            first, last = rides[0], rides[-1]
            if first.get("from_stop") and last.get("to_stop"):
                from_stop = first["from_stop"]
                to_stop = last["to_stop"]
        for label in _plan_bus_labels(plan):
            if label and label not in seen:
                seen.add(label)
                lines.append(label)
            if len(lines) >= 5:
                break
        if len(lines) >= 5:
            break
    return {
        "bus_lines": lines[:5],
        "bus_from_stop": from_stop,
        "bus_to_stop": to_stop,
    }


def _short_line_name(raw: str) -> str:
    return re.split(r"[（(]", raw.strip(), maxsplit=1)[0].strip()


def _segment_buslines(segment: dict[str, Any]) -> list[dict[str, Any]]:
    bus = segment.get("bus") or {}
    buslines = bus.get("buslines") if isinstance(bus, dict) else None
    if not buslines and isinstance(bus, list):
        buslines = bus
    return [line for line in (buslines or []) if isinstance(line, dict)]


def _plan_bus_labels(plan: dict[str, Any]) -> list[str]:
    """Display labels for one AMap transit plan.

    Same-segment buslines are alternatives (listed separately).
    Cross-segment rides are a transfer chain joined with " → ".
    """
    per_segment: list[list[str]] = []
    for segment in plan.get("segments") or []:
        names: list[str] = []
        seen: set[str] = set()
        for line in _segment_buslines(segment):
            short = _short_line_name(str(line.get("name") or ""))
            if short and short not in seen:
                seen.add(short)
                names.append(short)
        if names:
            per_segment.append(names)
    if not per_segment:
        return []
    if len(per_segment) == 1:
        return per_segment[0]
    # Transfer: primary line per boarding segment.
    return [" → ".join(names[0] for names in per_segment)]


def _extract_bus_rides(plan: dict[str, Any]) -> list[dict[str, str | None]]:
    rides: list[dict[str, str | None]] = []
    for segment in plan.get("segments") or []:
        for line in _segment_buslines(segment):
            raw = str(line.get("name") or "").strip()
            if not raw:
                continue
            short = _short_line_name(raw)
            if not short:
                continue
            departure = line.get("departure_stop") or line.get("departureStop") or {}
            arrival = line.get("arrival_stop") or line.get("arrivalStop") or {}
            from_name = str(departure.get("name") or "").strip() or None
            to_name = str(arrival.get("name") or "").strip() or None
            rides.append({"line": short, "from_stop": from_name, "to_stop": to_name})
    return rides
