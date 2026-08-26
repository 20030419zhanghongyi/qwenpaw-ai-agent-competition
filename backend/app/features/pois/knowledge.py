"""Source-attributed operational metadata and cultural graph for canonical POIs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parents[4] / "data" / "poi_knowledge_graph.json"
_POIS_PATH = Path(__file__).resolve().parents[4] / "data" / "pois.json"
_CANONICAL_TO_LEGACY = {
    "poi_0001": "poi_ruins_st_paul",
    "poi_0002": "poi_paixao",
    "poi_0003": "poi_mount_fortress",
    "poi_0004": "poi_senado",
    "poi_0008": "poi_rua_cunha",
    "poi_0009": "poi_st_dominic",
    "poi_0011": "poi_ama",
    "poi_0012": "poi_taipa_houses",
    "poi_0015": "poi_mandarin_house",
    "poi_0016": "poi_florindo",
    "poi_0017": "poi_lilau",
    "poi_0018": "poi_fatong",
    "poi_0030": "poi_sv_lazaro",
    "poi_0049": "poi_na_tcha",
    "poi_0050": "poi_st_lawrence",
    "poi_0051": "poi_dom_pedro_v",
    "poi_0052": "poi_st_joseph",
    "poi_0053": "poi_st_augustine",
    "poi_0054": "poi_cathedral",
    "poi_0055": "poi_holy_house_mercy",
    "poi_0056": "poi_leal_senado",
    "poi_0057": "poi_lou_kau",
    "poi_0098": "poi_carmo",
    "poi_0129": "poi_ho_tung_library",
    "poi_0133": "poi_old_city_walls",
    "poi_0168": "poi_xiahuan",
    "poi_0170": "poi_moorish_barracks",
    "poi_0234": "poi_coloane_chapel",
    "poi_0238": "poi_coloane_pier",
    "poi_0241": "poi_eanes_square",
}


@lru_cache(maxsize=1)
def _records() -> dict[str, dict[str, Any]]:
    """Load the versioned registry once; serving opening hours never uses the network."""
    payload = json.loads(_PATH.read_text(encoding="utf-8"))
    return {record["poi_id"]: record for record in payload["pois"]}


@lru_cache(maxsize=1)
def _poi_content() -> dict[str, dict[str, Any]]:
    payload = json.loads(_POIS_PATH.read_text(encoding="utf-8"))
    return {record["id"]: record for record in payload["pois"] if record.get("id")}


def get_poi_summary(poi_id: str) -> dict[str, str | None]:
    records = _poi_content()
    record = records.get(poi_id) or records.get(_CANONICAL_TO_LEGACY.get(poi_id, ""), {})
    return {
        "summary_zh_cn": record.get("intro"),
        "summary_zh_tw": record.get("intro_zh_tw"),
        "summary_en": record.get("intro_en"),
        "summary_pt": record.get("intro_pt"),
    }


def get_operational_metadata(poi_ids: list[str], language: str) -> dict[str, Any]:
    records = _records()
    entries = []
    for poi_id in dict.fromkeys(poi_ids):
        record = records.get(poi_id)
        if not record or not record.get("opening_hours"):
            continue
        hours = record["opening_hours"]
        entries.append(
            {
                "poi_id": poi_id,
                "name": record.get(f"name_{language}") or record.get("name_en") or poi_id,
                "status": hours.get("status", "verified-schedule"),
                "regular": hours.get("regular", []),
                "last_entry": hours.get("last_entry"),
                "closed_days": hours.get("closed_days", []),
                "special_note": hours.get("special_note"),
                "checked_at": hours.get("checked_at"),
                "source": hours.get("source"),
            }
        )
    return {
        "status": "verified-schedule" if entries else "unavailable",
        "entries": entries,
        "coverage": {"requested": len(set(poi_ids)), "verified": len(entries)},
        "sources": [item["source"] for item in entries if item.get("source")],
    }


def get_knowledge_subgraph(poi_ids: list[str]) -> dict[str, Any]:
    records = _records()
    requested = set(poi_ids)
    nodes = [records[poi_id] for poi_id in requested if poi_id in records]
    edges = [
        {"source": node["poi_id"], **edge}
        for node in nodes
        for edge in node.get("relations", [])
        if not requested or edge.get("target_poi_id") in requested
    ]
    return {"nodes": nodes, "edges": edges}
