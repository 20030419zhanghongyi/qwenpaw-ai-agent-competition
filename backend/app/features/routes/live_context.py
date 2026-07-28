"""Official live travel context with explicit safe network fallbacks."""

from __future__ import annotations

from datetime import date, datetime, timezone
from html import unescape
import re
import threading
import time
from typing import Any, Callable
from xml.etree import ElementTree

import httpx

SMG_CURRENT_WEATHER_URL = "https://www.smg.gov.mo/webdiss/c_actualweather_xml.php"
MGTO_EVENT_CALENDAR_URL = "https://www.macaotourism.gov.mo/en/events/calendar"
_CACHE_SECONDS = 600
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()
_UA = "MacauStoryWalk/0.1 (competition travel context)"


def _cached(key: str, loader: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_SECONDS:
            return hit[1]
    value = loader()
    with _cache_lock:
        _cache[key] = (now, value)
    return value


def _fetch(url: str) -> str | None:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _UA, "Accept": "application/xml,text/html"},
            follow_redirects=True,
            timeout=4.0,
            trust_env=False,
        )
        return response.text if response.status_code == 200 else None
    except httpx.HTTPError:
        return None


def _weather() -> dict[str, Any]:
    source = {"name": "Macao Meteorological and Geophysical Bureau", "url": SMG_CURRENT_WEATHER_URL}
    raw = _fetch(SMG_CURRENT_WEATHER_URL)
    if not raw:
        return {"status": "unavailable", "source": source}
    try:
        root = ElementTree.fromstring(raw)
        values = {
            re.sub(r"[^a-z0-9]", "", element.tag.lower()): (element.text or "").strip()
            for element in root.iter()
            if (element.text or "").strip()
        }
    except ElementTree.ParseError:
        return {"status": "unavailable", "source": source}

    def first(*keys: str) -> str | None:
        return next((values[key] for key in keys if values.get(key)), None)

    return {
        "status": "ok",
        "temperature_c": first("temperature", "temp", "macautemp"),
        "humidity_percent": first("humidity", "relativehumidity", "macauhumidity"),
        "rainfall_mm": first("rainfall", "hourlyrainfall", "rain"),
        "condition": first("weather", "weatherdesc", "weatherdescription"),
        "warning": first("warning", "warningmessage", "signal"),
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _events(target: date) -> dict[str, Any]:
    source = {
        "name": "Macao Government Tourism Office event calendar",
        "url": MGTO_EVENT_CALENDAR_URL,
    }
    raw = _fetch(MGTO_EVENT_CALENDAR_URL)
    if not raw:
        return {"status": "unavailable", "events": [], "source": source}
    text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
    excerpts: list[str] = []
    date_patterns = (
        f"{target.strftime('%B')} {target.day}",
        f"{target.strftime('%B')} {target.day:02d}",
    )
    for pattern in date_patterns:
        start = text.lower().find(pattern.lower())
        if start >= 0:
            excerpt = text[max(0, start - 100) : start + 240].strip()
            if excerpt and excerpt not in excerpts:
                excerpts.append(excerpt)
    return {
        "status": "ok",
        "events": excerpts[:3],
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_live_route_context(travel_date: str | None) -> dict[str, Any]:
    """Return source-attributed weather and official event signals for a route."""
    try:
        target = date.fromisoformat(travel_date) if travel_date else date.today()
    except ValueError:
        target = date.today()
    weather = _cached("weather", _weather)
    events = _cached(f"events:{target.isoformat()}", lambda: _events(target))
    notes: list[str] = []
    if weather.get("status") == "ok":
        details = [
            f"{weather['temperature_c']}°C" if weather.get("temperature_c") else None,
            weather.get("condition"),
            f"雨量 {weather['rainfall_mm']}mm" if weather.get("rainfall_mm") else None,
        ]
        summary = "，".join(item for item in details if item)
        if summary:
            notes.append(f"澳门气象局实时天气：{summary}")
        if weather.get("warning"):
            notes.append(f"气象提醒：{weather['warning']}")
    else:
        notes.append("暂未取得澳门气象局实时天气；请以现场官方预警为准")
    if events.get("status") == "ok" and events.get("events"):
        notes.append("澳门旅游局日历显示当日附近有公开活动，热门区域可能较繁忙")
    elif events.get("status") == "unavailable":
        notes.append("暂未取得澳门旅游局活动日历；未据此作实时人流判断")
    return {
        "travel_date": target.isoformat(),
        "weather": weather,
        "events": events,
        "notes": notes,
        "crowd_signal": "event-proxy" if events.get("events") else "unavailable",
    }
