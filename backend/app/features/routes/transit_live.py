"""Live Macao bus operations from the DSAT public web application."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import threading
import time
from typing import Any

import httpx

DSAT_BASE_URL = "https://bis.dsat.gov.mo"
DSAT_PORTAL_URL = f"{DSAT_BASE_URL}/macauweb/"
_CACHE_SECONDS = 25
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


def _token(params: dict[str, Any]) -> str:
    """Reproduce the request token shipped in DSAT's public bus web client."""
    query = "&".join(f"{key}={value}" for key, value in params.items())
    digest = list(hashlib.md5(query.encode(), usedforsecurity=False).hexdigest())
    stamp = datetime.now().strftime("%Y%m%d%H%M")
    digest[24:24] = stamp[8:]
    digest[12:12] = stamp[4:8]
    digest[4:4] = stamp[:4]
    return "".join(digest)


def _post(path: str, params: dict[str, Any]) -> dict[str, Any] | None:
    payload = {**params, "device": "web"}
    try:
        # DSAT's public endpoint currently serves an incomplete certificate chain on
        # some clients. Requests are restricted to the fixed official host.
        response = httpx.post(
            f"{DSAT_BASE_URL}{path}",
            data=payload,
            headers={
                "token": _token(payload),
                "User-Agent": "MacauStoryWalk/0.1",
                "Referer": DSAT_PORTAL_URL,
            },
            timeout=4.0,
            verify=False,
            trust_env=False,
        )
        if response.status_code != 200:
            return None
        value = response.json()
        return value if isinstance(value, dict) else None
    except (httpx.HTTPError, ValueError):
        return None


def _cached(key: str, loader) -> dict[str, Any]:
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_SECONDS:
            return hit[1]
    value = loader()
    with _lock:
        _cache[key] = (now, value)
    return value


def get_bus_operations(*, routes: list[str], language: str) -> dict[str, Any]:
    """Return live route changes, suspended stops and bus positions when supplied."""
    lang = {"zh-CN": "zh_cn", "zh-TW": "zh_tw", "pt": "pt"}.get(language, "en")
    route_names = list(dict.fromkeys(route.strip().upper() for route in routes if route.strip()))

    def load() -> dict[str, Any]:
        listing = _post("/macauweb/getRouteAndCompanyList.html", {"lang": lang})
        if not listing or listing.get("header") != "000":
            return {
                "status": "unavailable",
                "routes": [],
                "alerts": [],
                "source": {"name": "DSAT Bus Travelling System", "url": DSAT_PORTAL_URL},
            }
        route_list = (listing.get("data") or {}).get("routeList") or []
        changed = [
            {
                "route": str(item.get("routeName")),
                "operator_color": item.get("color"),
                "has_change": True,
                "suspended_stops": [],
                "buses": [],
            }
            for item in route_list
            if str(item.get("routeChange")) == "1"
        ]
        selected = route_names
        details = []
        alerts = changed if not selected else []
        for route_name in selected[:12]:
            matching = next(
                (item for item in route_list if str(item.get("routeName", "")).upper() == route_name),
                None,
            )
            if not matching:
                continue
            direction = str(matching.get("direction", "0"))
            route_data = _post(
                "/macauweb/getRouteData.html",
                {"routeName": route_name, "dir": direction, "lang": lang},
            )
            data = (route_data or {}).get("data") or {}
            suspended = [
                {
                    "stop_code": stop.get("staCode"),
                    "stop_name": stop.get("staName"),
                }
                for stop in data.get("routeInfo") or []
                if str(stop.get("suspendState")) == "1"
            ]
            buses = data.get("busInfo") or []
            entry = {
                "route": route_name,
                "operator_color": matching.get("color"),
                "has_change": str(matching.get("routeChange")) == "1",
                "suspended_stops": suspended,
                "buses": buses,
            }
            details.append(entry)
            if entry["has_change"] or suspended:
                alerts.append(entry)
        return {
            "status": "live",
            "routes": details or changed,
            "alerts": alerts,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "cache_seconds": _CACHE_SECONDS,
            "source": {"name": "DSAT Bus Travelling System", "url": DSAT_PORTAL_URL},
        }

    return _cached(f"{lang}:{','.join(route_names) or 'alerts'}", load)
