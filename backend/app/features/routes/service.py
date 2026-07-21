"""Application service for route-template API operations."""

from app.models.user import Preference

from .matcher import match_routes
from .repository import SqlAlchemyRouteRepository, route_repository


class RouteService:
    def __init__(self, repository: SqlAlchemyRouteRepository) -> None:
        self._repository = repository

    def list_templates(self) -> list[dict]:
        return self._repository.list_templates()

    def get_template(self, route_id: str) -> dict | None:
        return self._repository.get_template(route_id)

    def upsert_constructed_template(self, route: dict) -> dict:
        return self._repository.upsert_constructed_template(route)

    def match(self, preference: Preference) -> list[dict]:
        return match_routes(preference)


route_service = RouteService(route_repository)
