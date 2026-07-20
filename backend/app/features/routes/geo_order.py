"""Geographic node ordering for walkable itineraries (esp. Cotai / Taipa).

District-name sorting is too coarse for 路氹. Pure nearest-neighbor also
misleads: from the Venetian, Studio City can look like a short first hop, and
inserting 龙环 mid-strip (威尼斯人→龙环→新濠→永利) forces a north spur then a
return past the Strip toward City of Dreams / Wynn.

Verified corridor (Amap coords + Cotai / 官也街 travel guides):
  0) Northern Taipa fringe (龙环葡韵) — do before entering the Strip
  1) Strip Europe west cluster (威尼斯人 / 巴黎人 / 伦敦人)
  2) Strip mid (新濠天地)
  3) Strip east Wynn cluster (永利皇宫 / 缆车 / 表演湖)
  4) Strip south (新濠影汇)

Default with 龙环 present: 龙环 → 威尼斯人 → … → 新濠 → 永利 (not
威尼斯人 → 龙环 → 新濠 → 永利, which backtracks).
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .poi_metadata import get_poi_metadata

_COTAI_DISTRICTS = {"路氹填海区", "嘉模堂区"}

# Keep these together; expand in walking / template order.
_EUROPE_CLUSTER = ("poi_0020", "poi_0021", "poi_0107")  # 威尼斯人→巴黎人→伦敦人
_WYNN_CLUSTER = ("poi_0027", "poi_0230", "poi_0231")  # 永利→缆车→表演湖
_CLUSTER_MEMBERS: dict[str, tuple[str, ...]] = {
    **{poi_id: _EUROPE_CLUSTER for poi_id in _EUROPE_CLUSTER},
    **{poi_id: _WYNN_CLUSTER for poi_id in _WYNN_CLUSTER},
}


def _coords(poi_id: str) -> tuple[float, float] | None:
    poi = get_poi_metadata(poi_id) or {}
    raw = poi.get("coordinates")
    if isinstance(raw, dict):
        lat, lng = raw.get("lat"), raw.get("lng")
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            return float(lat), float(lng)
    lat, lng = poi.get("latitude"), poi.get("longitude")
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return float(lat), float(lng)
    return None


def _dist_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b
    mean_lat = math.radians((lat1 + lat2) / 2.0)
    dx = (lng2 - lng1) * 111_320 * math.cos(mean_lat)
    dy = (lat2 - lat1) * 110_540
    return math.hypot(dx, dy)


def _cotai_corridor_bucket(lat: float, lng: float) -> int:
    """Ordered Cotai / Taipa walking bands (north spur → west→east → south)."""
    if lat >= 22.149:
        return 0  # 龙环葡韵一带（偏北，先逛再进金光大道）
    if lat < 22.139:
        return 4  # 南段：新濠影汇等
    if lng < 113.568:
        return 1  # 金光西：威尼斯人 / 巴黎人
    if lng < 113.573:
        return 2  # 中段：伦敦人 / 新濠天地
    return 3  # 东段：永利皇宫簇


def _centroid(poi_ids: Iterable[str], coords: dict[str, tuple[float, float]]) -> tuple[float, float]:
    points = [coords[poi_id] for poi_id in poi_ids if poi_id in coords]
    if not points:
        return (0.0, 0.0)
    lat = sum(p[0] for p in points) / len(points)
    lng = sum(p[1] for p in points) / len(points)
    return lat, lng


def _unit_key(poi_ids: list[str], coords: dict[str, tuple[float, float]]) -> tuple:
    lat, lng = _centroid(poi_ids, coords)
    bucket = _cotai_corridor_bucket(lat, lng)
    # Within a band: west→east, then north→south.
    return (bucket, lng, -lat, poi_ids[0])


def _collapse_to_units(
    poi_ids: list[str],
    coords: dict[str, tuple[float, float]],
) -> list[list[str]]:
    """Collapse Europe / Wynn members into sticky units; preserve relative order."""
    remaining = list(poi_ids)
    units: list[list[str]] = []
    seen_clusters: set[tuple[str, ...]] = set()

    while remaining:
        poi_id = remaining.pop(0)
        cluster = _CLUSTER_MEMBERS.get(poi_id)
        if cluster is None:
            units.append([poi_id])
            continue
        if cluster in seen_clusters:
            continue
        seen_clusters.add(cluster)
        present = {poi_id, *remaining}
        unit = [member for member in cluster if member in present]
        # Drop clustered ids from the remaining queue.
        remaining = [item for item in remaining if item not in cluster]
        units.append(unit)
    return units


def _expand_units(units: list[list[str]]) -> list[str]:
    return [poi_id for unit in units for poi_id in unit]


def _order_units_nearest_neighbor(
    units: list[list[str]],
    coords: dict[str, tuple[float, float]],
    *,
    start_poi_id: str | None = None,
) -> list[list[str]]:
    if len(units) <= 1:
        return units

    centroids = {
        id(unit): _centroid(unit, coords) if any(p in coords for p in unit) else None
        for unit in units
    }
    usable = [unit for unit in units if centroids[id(unit)] is not None]
    missing = [unit for unit in units if centroids[id(unit)] is None]
    if not usable:
        return units

    # Prefer corridor sort (stable tourist flow) over pure NN, which can yank
    # Studio City ahead of 龙环 from the Venetian.
    ranked = sorted(usable, key=lambda unit: _unit_key(unit, coords))

    start_unit: list[str] | None = None
    if start_poi_id:
        for unit in ranked:
            if start_poi_id in unit:
                start_unit = unit
                break

    if start_unit is None:
        return [*ranked, *missing]

    start_bucket = _unit_key(start_unit, coords)[0]
    rest = [
        unit
        for unit in ranked
        if unit is not start_unit and _unit_key(unit, coords)[0] >= start_bucket
    ]
    earlier = [
        unit
        for unit in ranked
        if unit is not start_unit and _unit_key(unit, coords)[0] < start_bucket
    ]
    # Northern spur (龙环) sits in an earlier band — keep it *before* a Strip
    # start so we do not visit it mid-corridor and backtrack.
    if earlier and start_bucket >= 1:
        ordered = [*earlier, start_unit, *rest]
    else:
        ordered = [start_unit, *rest, *earlier]
    return [*ordered, *missing]


def _order_by_corridor(
    poi_ids: list[str],
    coords: dict[str, tuple[float, float]],
    *,
    start_id: str | None = None,
) -> list[str]:
    known = [poi_id for poi_id in poi_ids if poi_id in coords]
    missing = [poi_id for poi_id in poi_ids if poi_id not in coords]
    if not known:
        return list(poi_ids)

    units = _collapse_to_units(known, coords)
    ordered_units = _order_units_nearest_neighbor(units, coords, start_poi_id=start_id)
    return [*_expand_units(ordered_units), *missing]


def route_is_cotai_heavy(nodes: list[dict]) -> bool:
    hits = 0
    for node in nodes:
        poi = get_poi_metadata(str(node.get("poi_id") or "")) or {}
        if str(poi.get("district") or "") in _COTAI_DISTRICTS:
            hits += 1
    return hits >= 2


def reorder_nodes_geographically(
    nodes: list[dict],
    *,
    start_poi_id: str | None = None,
) -> tuple[list[dict], bool]:
    """Reorder middle nodes along the Cotai corridor; keep entry/exit anchors."""
    ordered = sorted(nodes, key=lambda item: item.get("order", 0))
    entry = [node for node in ordered if node.get("anchor") == "entry"]
    exit_nodes = [node for node in ordered if node.get("anchor") == "exit"]
    middle = [node for node in ordered if node.get("anchor") not in {"entry", "exit"}]
    if len(middle) <= 1:
        return ordered, False

    original_ids = [node["poi_id"] for node in middle]
    coords = {
        node["poi_id"]: xy
        for node in middle
        if (xy := _coords(str(node["poi_id"]))) is not None
    }
    if len(coords) < 2:
        return ordered, False

    start = start_poi_id if start_poi_id in coords else None
    if start is None and entry:
        port_xy = _coords(str(entry[0]["poi_id"]))
        if port_xy:
            start = min(coords.keys(), key=lambda poi_id: _dist_m(port_xy, coords[poi_id]))

    id_order = _order_by_corridor(original_ids, coords, start_id=start)
    by_id = {node["poi_id"]: node for node in middle}
    new_middle = [by_id[poi_id] for poi_id in id_order if poi_id in by_id]
    changed = [node["poi_id"] for node in new_middle] != original_ids
    result = [*entry, *new_middle, *exit_nodes]
    for index, node in enumerate(result, start=1):
        node["order"] = index
    return result, changed
