"""PostgreSQL repository for route templates and ordered stops."""

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import RouteTemplate, RouteTemplateStop
from app.db.session import SessionLocal
from app.features.pois.repository import canonical_poi_id

# Generated theme-day itineraries live in the same table so trip/adjust/get
# can resolve them, but must not pollute the curated preset catalog.
THEME_DAY_ID_PREFIX = "theme_day_"


class SqlAlchemyRouteRepository:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _query():
        return select(RouteTemplate).options(selectinload(RouteTemplate.stops))

    @staticmethod
    def _to_dict(template: RouteTemplate) -> dict:
        stops = sorted(template.stops, key=lambda stop: stop.stop_order)
        return {
            "id": template.id,
            "name": template.name,
            "theme": template.category,
            "duration_label": template.duration,
            "duration_hours": template.duration_hours,
            "walk_distance_km": template.walk_distance_km,
            "physical_level": template.physical_level,
            "suitable_for": list(template.suitable_for),
            "nodes": [
                {
                    "poi_id": stop.poi_id,
                    "order": stop.stop_order,
                    "suggested_stay_min": stop.stay_minutes,
                    "note": stop.note,
                    "replaceable_with": list(stop.replaceable_with),
                }
                for stop in stops
            ],
            "description": template.description,
        }

    def list_templates(self) -> list[dict]:
        with self._session_factory() as session:
            templates = session.scalars(
                self._query()
                .where(~RouteTemplate.id.startswith(THEME_DAY_ID_PREFIX))
                .order_by(RouteTemplate.sort_order, RouteTemplate.id)
            ).all()
            return [self._to_dict(template) for template in templates]

    def get_template(self, route_id: str) -> dict | None:
        with self._session_factory() as session:
            template = session.scalar(self._query().where(RouteTemplate.id == route_id))
            return self._to_dict(template) if template is not None else None

    def upsert_constructed_template(self, route: dict) -> dict:
        """Persist a constructed (often theme-day) itinerary so trip APIs can resolve it.

        Overwrites an existing row with the same id (last match wins). Only stores
        fields that fit ``route_templates`` / ``route_template_stops``.
        """
        route_id = str(route.get("id") or "").strip()
        if not route_id:
            raise ValueError("Constructed route is missing an id")

        nodes = sorted(route.get("nodes") or [], key=lambda node: node.get("order", 0))
        stop_rows: list[dict] = []
        seen_orders: set[int] = set()
        for index, node in enumerate(nodes, start=1):
            poi_id = canonical_poi_id(str(node.get("poi_id") or "").strip())
            if not poi_id:
                continue
            stop_order = int(node.get("order") or index)
            if stop_order in seen_orders:
                stop_order = index
            while stop_order in seen_orders:
                stop_order += 1
            seen_orders.add(stop_order)
            replacements = [
                canonical_poi_id(str(item))
                for item in (node.get("replaceable_with") or [])
                if str(item).strip()
            ]
            stop_rows.append(
                {
                    "poi_id": poi_id,
                    "stop_order": stop_order,
                    "stay_minutes": int(node.get("suggested_stay_min") or 30),
                    "note": str(node.get("note") or ""),
                    "replaceable_with": replacements,
                }
            )
        if not stop_rows:
            raise ValueError(f"Constructed route has no stops: {route_id}")

        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            template = session.get(RouteTemplate, route_id)
            if template is None:
                template = RouteTemplate(id=route_id, created_at=now, sort_order=10_000)
                session.add(template)
            template.name = str(route.get("name") or route_id)
            template.description = str(route.get("description") or "")
            template.duration = str(
                route.get("duration_label") or route.get("duration") or "一日"
            )
            template.category = str(route.get("theme") or "generated")
            template.duration_hours = float(route.get("duration_hours") or 3.5)
            template.walk_distance_km = float(route.get("walk_distance_km") or 1.0)
            template.physical_level = str(route.get("physical_level") or "medium")
            template.suitable_for = list(route.get("suitable_for") or [])
            template.updated_at = now
            session.flush()
            session.execute(
                delete(RouteTemplateStop).where(
                    RouteTemplateStop.route_template_id == route_id
                )
            )
            session.flush()
            session.add_all(
                [
                    RouteTemplateStop(
                        route_template_id=route_id,
                        poi_id=stop["poi_id"],
                        stop_order=stop["stop_order"],
                        stay_minutes=stop["stay_minutes"],
                        note=stop["note"],
                        replaceable_with=stop["replaceable_with"],
                    )
                    for stop in stop_rows
                ]
            )
            session.commit()
            session.refresh(template)
            # Re-load with stops for a consistent dict shape.
            loaded = session.scalar(self._query().where(RouteTemplate.id == route_id))
            assert loaded is not None
            return self._to_dict(loaded)


route_repository = SqlAlchemyRouteRepository()


def list_templates() -> list[dict]:
    return route_repository.list_templates()


def get_template(route_id: str) -> dict | None:
    return route_repository.get_template(route_id)


def upsert_constructed_template(route: dict) -> dict:
    return route_repository.upsert_constructed_template(route)
