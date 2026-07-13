"""Canonical-ID view of legacy POI planning metadata.

Route templates live in PostgreSQL. The planning rules still need curated theme,
district, and suitability tags that are not yet columns on the POI table.
"""

from functools import lru_cache

from app.db.data import load_pois
from app.features.pois.repository import canonical_poi_id


def _metadata_score(poi: dict) -> int:
    return sum(
        len(poi.get(field) or [])
        for field in ("theme", "suitable_for")
    ) + sum(bool(poi.get(field)) for field in ("district", "intro", "history"))


@lru_cache(maxsize=1)
def _canonical_index() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for source in load_pois():
        poi_id = canonical_poi_id(source["id"])
        candidate = {**source, "id": poi_id}
        current = index.get(poi_id)
        if current is None or _metadata_score(candidate) > _metadata_score(current):
            index[poi_id] = candidate
    return index


def get_poi_metadata(poi_id: str) -> dict | None:
    return _canonical_index().get(canonical_poi_id(poi_id))


def list_poi_metadata() -> list[dict]:
    return list(_canonical_index().values())
