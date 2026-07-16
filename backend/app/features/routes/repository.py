"""PostgreSQL repository for route templates and ordered stops."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import RouteTemplate
from app.db.session import SessionLocal


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
                self._query().order_by(RouteTemplate.sort_order, RouteTemplate.id)
            ).all()
            return [self._to_dict(template) for template in templates]

    def get_template(self, route_id: str) -> dict | None:
        with self._session_factory() as session:
            template = session.scalar(self._query().where(RouteTemplate.id == route_id))
            return self._to_dict(template) if template is not None else None


route_repository = SqlAlchemyRouteRepository()


def list_templates() -> list[dict]:
    return route_repository.list_templates()


def get_template(route_id: str) -> dict | None:
    return route_repository.get_template(route_id)
