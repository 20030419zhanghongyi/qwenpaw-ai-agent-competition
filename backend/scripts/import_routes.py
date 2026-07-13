"""Import route templates from read-only JSON into PostgreSQL."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from sqlalchemy import delete, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.models import Poi, RouteTemplate, RouteTemplateStop  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.features.pois.repository import canonical_poi_id  # noqa: E402


@dataclass(frozen=True)
class RouteStopImportRow:
    poi_id: str
    stop_order: int
    stay_minutes: int
    note: str
    replaceable_with: list[str]


@dataclass(frozen=True)
class RouteImportRow:
    route_id: str
    name: str
    description: str
    duration: str
    category: str
    duration_hours: float
    walk_distance_km: float
    physical_level: str
    suitable_for: list[str]
    sort_order: int
    stops: list[RouteStopImportRow]


@dataclass(frozen=True)
class ImportResult:
    templates_read: int
    inserted: int
    updated: int
    stops_written: int
    legacy_ids_converted: int


def read_route_rows(source_path: Path) -> tuple[list[RouteImportRow], int]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    source_routes = payload.get("routes")
    if not isinstance(source_routes, list):
        raise ValueError("Route JSON must contain a routes list")

    rows: list[RouteImportRow] = []
    seen_ids: set[str] = set()
    conversions = 0
    for sort_order, route in enumerate(source_routes):
        route_id = str(route.get("id", "")).strip()
        if not route_id or route_id in seen_ids:
            raise ValueError(f"Missing or duplicate route id: {route_id!r}")
        seen_ids.add(route_id)

        stops: list[RouteStopImportRow] = []
        seen_orders: set[int] = set()
        for node in route.get("nodes", []):
            original_id = str(node["poi_id"])
            poi_id = canonical_poi_id(original_id)
            conversions += poi_id != original_id
            stop_order = int(node["order"])
            if stop_order in seen_orders:
                raise ValueError(f"Duplicate stop order in route {route_id}: {stop_order}")
            seen_orders.add(stop_order)
            replacements = []
            for replacement in node.get("replaceable_with", []):
                canonical = canonical_poi_id(str(replacement))
                conversions += canonical != replacement
                replacements.append(canonical)
            stops.append(
                RouteStopImportRow(
                    poi_id=poi_id,
                    stop_order=stop_order,
                    stay_minutes=int(node["suggested_stay_min"]),
                    note=str(node.get("note", "")),
                    replaceable_with=replacements,
                )
            )

        rows.append(
            RouteImportRow(
                route_id=route_id,
                name=str(route["name"]),
                description=str(route.get("description", "")),
                duration=str(route["duration_label"]),
                category=str(route["theme"]),
                duration_hours=float(route["duration_hours"]),
                walk_distance_km=float(route["walk_distance_km"]),
                physical_level=str(route["physical_level"]),
                suitable_for=list(route.get("suitable_for", [])),
                sort_order=sort_order,
                stops=stops,
            )
        )
    return rows, conversions


def upsert_routes(rows: list[RouteImportRow], *, session_factory=SessionLocal) -> ImportResult:
    referenced_poi_ids = {
        poi_id
        for route in rows
        for stop in route.stops
        for poi_id in [stop.poi_id, *stop.replaceable_with]
    }
    with session_factory() as session:
        available_poi_ids = set(
            session.scalars(select(Poi.poi_id).where(Poi.poi_id.in_(referenced_poi_ids)))
        )
        missing = sorted(referenced_poi_ids - available_poi_ids)
        if missing:
            raise ValueError(f"Routes reference missing canonical POIs: {missing}")

        existing_ids = set(
            session.scalars(
                select(RouteTemplate.id).where(
                    RouteTemplate.id.in_([row.route_id for row in rows])
                )
            )
        )
        now = datetime.now(timezone.utc)
        for row in rows:
            template = session.get(RouteTemplate, row.route_id)
            if template is None:
                template = RouteTemplate(id=row.route_id, created_at=now)
                session.add(template)
            template.name = row.name
            template.description = row.description
            template.duration = row.duration
            template.category = row.category
            template.duration_hours = row.duration_hours
            template.walk_distance_km = row.walk_distance_km
            template.physical_level = row.physical_level
            template.suitable_for = row.suitable_for
            template.sort_order = row.sort_order
            template.updated_at = now
            session.flush()
            session.execute(
                delete(RouteTemplateStop).where(
                    RouteTemplateStop.route_template_id == row.route_id
                )
            )
            session.flush()
            session.add_all(
                [
                    RouteTemplateStop(
                        route_template_id=row.route_id,
                        poi_id=stop.poi_id,
                        stop_order=stop.stop_order,
                        stay_minutes=stop.stay_minutes,
                        note=stop.note,
                        replaceable_with=stop.replaceable_with,
                    )
                    for stop in row.stops
                ]
            )
        session.commit()

    inserted = sum(row.route_id not in existing_ids for row in rows)
    return ImportResult(
        templates_read=len(rows),
        inserted=inserted,
        updated=len(rows) - inserted,
        stops_written=sum(len(row.stops) for row in rows),
        legacy_ids_converted=0,
    )


def import_route_file(source_path: Path) -> ImportResult:
    rows, conversions = read_route_rows(source_path)
    result = upsert_routes(rows)
    return ImportResult(
        templates_read=result.templates_read,
        inserted=result.inserted,
        updated=result.updated,
        stops_written=result.stops_written,
        legacy_ids_converted=conversions,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to the existing routes.json")
    args = parser.parse_args()
    result = import_route_file(args.source.resolve(strict=True))
    print(json.dumps(result.__dict__, ensure_ascii=False))


if __name__ == "__main__":
    main()
