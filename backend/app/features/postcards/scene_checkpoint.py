"""Batch checkpoint for postcard scene research + generation.

Written to::

    data/postcard_scenes/_checkpoint.json

Phases:
  - ``research`` — POI landmarks + reference photos collected
  - ``generate`` — SVG slots drawn (future continuation)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.features.postcards.scene_library import TIME_SLOTS, scene_path, scenes_root

CHECKPOINT_NAME = "_checkpoint.json"
PHASE_RESEARCH = "research"
PHASE_GENERATE = "generate"


def checkpoint_path() -> Path:
    return scenes_root() / CHECKPOINT_NAME


def load_checkpoint() -> dict[str, Any]:
    path = checkpoint_path()
    if not path.is_file():
        return {
            "version": 1,
            "phase": None,
            "updated_at": None,
            "agent_id": "scene",
            "pois": {},
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "version": 1,
            "phase": None,
            "updated_at": None,
            "agent_id": "scene",
            "pois": {},
        }
    if not isinstance(raw, dict):
        return {
            "version": 1,
            "phase": None,
            "updated_at": None,
            "agent_id": "scene",
            "pois": {},
        }
    raw.setdefault("pois", {})
    raw.setdefault("agent_id", "scene")
    raw.setdefault("version", 1)
    return raw


def save_checkpoint(data: dict[str, Any]) -> Path:
    path = checkpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def mark_research(
    checkpoint: dict[str, Any],
    *,
    poi_id: str,
    name_zh: str,
    has_ref: bool,
    landmarks_chars: int,
    sources: list[str],
) -> None:
    pois = checkpoint.setdefault("pois", {})
    entry = pois.get(poi_id) if isinstance(pois.get(poi_id), dict) else {}
    entry.update(
        {
            "name_zh": name_zh,
            "researched": True,
            "has_ref": has_ref,
            "landmarks_chars": landmarks_chars,
            "sources": sources[:8],
            "slots": entry.get("slots")
            if isinstance(entry.get("slots"), dict)
            else {s: "pending" for s in TIME_SLOTS},
        }
    )
    pois[poi_id] = entry
    checkpoint["phase"] = PHASE_RESEARCH


def mark_slot(
    checkpoint: dict[str, Any],
    *,
    poi_id: str,
    slot: str,
    status: str,
) -> None:
    pois = checkpoint.setdefault("pois", {})
    entry = pois.get(poi_id) if isinstance(pois.get(poi_id), dict) else {}
    slots = entry.get("slots") if isinstance(entry.get("slots"), dict) else {}
    slots[slot] = status
    entry["slots"] = slots
    pois[poi_id] = entry
    checkpoint["phase"] = PHASE_GENERATE


def research_summary(checkpoint: dict[str, Any]) -> dict[str, int]:
    pois = checkpoint.get("pois") or {}
    researched = sum(1 for v in pois.values() if isinstance(v, dict) and v.get("researched"))
    with_ref = sum(1 for v in pois.values() if isinstance(v, dict) and v.get("has_ref"))
    return {"pois": len(pois), "researched": researched, "with_ref": with_ref}


def slot_status_from_disk(poi_id: str, slot: str) -> str:
    path = scene_path(poi_id, slot)
    return "done" if path.is_file() else "pending"
