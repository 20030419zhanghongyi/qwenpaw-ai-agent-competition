"""Business rules for creating trips, checking in, and calculating progress."""

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from uuid import uuid4

from app.db.session import SessionLocal
from app.features.pois.repository import PoiRepository
from app.features.routes.repository import get_template
from app.features.users.repository import user_repository

from .models import (
    Trip,
    TripProgress,
    TripProgressResponse,
    TripResponse,
    TripStatus,
    TripWithProgressResponse,
)
from .repository import SqlAlchemyTripRepository, trip_repository


class TripNotFoundError(LookupError):
    pass


class RouteNotFoundError(LookupError):
    pass


class InvalidRouteError(ValueError):
    pass


class PoiNotInTripError(ValueError):
    pass


class PoiTooFarError(ValueError):
    pass


def distance_meters(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    """Great-circle distance; coordinates are not retained after this check."""
    lat_delta = radians(latitude_b - latitude_a)
    lon_delta = radians(longitude_b - longitude_a)
    area = sin(lat_delta / 2) ** 2 + cos(radians(latitude_a)) * cos(radians(latitude_b)) * sin(
        lon_delta / 2
    ) ** 2
    return 2 * 6_371_000 * asin(sqrt(area))


class TripService:
    def __init__(self, repository: SqlAlchemyTripRepository) -> None:
        self._repository = repository

    @staticmethod
    def _extract_stop_poi_ids(route: dict) -> list[str]:
        nodes = sorted(route.get("nodes") or [], key=lambda node: node.get("order", 0))
        stop_poi_ids: list[str] = []
        seen: set[str] = set()
        for node in nodes:
            poi_id = node.get("poi_id")
            if not isinstance(poi_id, str) or not poi_id or poi_id in seen:
                continue
            seen.add(poi_id)
            stop_poi_ids.append(poi_id)
        return stop_poi_ids

    @staticmethod
    def calculate_progress(trip: Trip) -> TripProgress:
        total = len(trip.stop_poi_ids)
        checked = set(trip.checked_in_poi_ids)
        completed = sum(poi_id in checked for poi_id in trip.stop_poi_ids)
        next_poi_id = next(
            (poi_id for poi_id in trip.stop_poi_ids if poi_id not in checked),
            None,
        )
        return TripProgress(
            total_stops=total,
            completed_stops=completed,
            completion_ratio=completed / total if total else 0.0,
            next_poi_id=next_poi_id,
        )

    def _with_progress(self, trip: Trip) -> TripWithProgressResponse:
        progress = self.calculate_progress(trip)
        return TripWithProgressResponse(
            trip=TripResponse.model_validate(trip.model_dump()),
            progress=TripProgressResponse.model_validate(progress.model_dump()),
        )

    def create_trip(
        self,
        user_id: str,
        route_id: str,
        stop_poi_ids: list[str] | None = None,
    ) -> TripWithProgressResponse:
        route = get_template(route_id)
        if route is None:
            raise RouteNotFoundError(f"Route not found: {route_id}")

        if stop_poi_ids is not None:
            resolved_stops = self._normalize_stop_poi_ids(stop_poi_ids)
            if not resolved_stops:
                raise InvalidRouteError("stop_poi_ids must include at least one POI")
        else:
            resolved_stops = self._extract_stop_poi_ids(route)
            if not resolved_stops:
                raise InvalidRouteError(f"Route has no valid POI stops: {route_id}")

        with SessionLocal() as session:
            pois = PoiRepository(session).get_by_ids(resolved_stops)
        missing_poi_ids = [poi_id for poi_id in resolved_stops if poi_id not in pois]
        if missing_poi_ids:
            raise InvalidRouteError(
                f"Route references unknown POIs: {', '.join(missing_poi_ids)}"
            )

        now = datetime.now(timezone.utc)
        trip = Trip(
            trip_id=str(uuid4()),
            user_id=user_id,
            route_id=route_id,
            status=TripStatus.ACTIVE,
            stop_poi_ids=resolved_stops,
            checked_in_poi_ids=[],
            created_at=now,
            updated_at=now,
        )
        created = self._repository.create_trip(trip)
        user_repository.record_trip_memory(user_id, route_id)
        return self._with_progress(created)

    @staticmethod
    def _normalize_stop_poi_ids(stop_poi_ids: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for poi_id in stop_poi_ids:
            if not isinstance(poi_id, str):
                continue
            cleaned = poi_id.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized

    def get_trip(self, trip_id: str) -> TripWithProgressResponse:
        trip = self._repository.get_trip(trip_id)
        if trip is None:
            raise TripNotFoundError(f"Trip not found: {trip_id}")
        return self._with_progress(trip)

    def get_current_trip(self, user_id: str) -> TripWithProgressResponse:
        trip = self._repository.get_user_current_trip(user_id)
        if trip is None:
            raise TripNotFoundError(f"Active trip not found for user: {user_id}")
        return self._with_progress(trip)

    def check_in(self, trip_id: str, poi_id: str) -> TripWithProgressResponse:
        trip = self._repository.get_trip(trip_id)
        if trip is None:
            raise TripNotFoundError(f"Trip not found: {trip_id}")
        if poi_id not in trip.stop_poi_ids:
            raise PoiNotInTripError(f"POI is not part of trip {trip_id}: {poi_id}")

        if poi_id not in trip.checked_in_poi_ids:
            trip = self._repository.add_checkin(trip_id, poi_id)
            if trip is None:
                raise TripNotFoundError(f"Trip not found: {trip_id}")
        return self._with_progress(trip)

    def check_in_at_location(
        self,
        trip_id: str,
        poi_id: str,
        *,
        longitude: float,
        latitude: float,
        radius_m: float,
        accuracy_m: float | None = None,
    ) -> TripWithProgressResponse:
        trip = self._repository.get_trip(trip_id)
        if trip is None:
            raise TripNotFoundError(f"Trip not found: {trip_id}")
        if poi_id not in trip.stop_poi_ids:
            raise PoiNotInTripError(f"POI is not part of trip {trip_id}: {poi_id}")
        with SessionLocal() as session:
            poi = PoiRepository(session).get_by_id(poi_id)
        if poi is None:
            raise PoiNotInTripError(f"POI not found: {poi_id}")
        distance = distance_meters(latitude, longitude, poi.latitude, poi.longitude)
        tolerance = radius_m + min(accuracy_m or 0, 80)
        if distance > tolerance:
            raise PoiTooFarError(
                "You are "
                f"{round(distance)}m from this stop; move within {round(tolerance)}m to check in"
            )
        return self.check_in(trip_id, poi_id)

    def get_progress(self, trip_id: str) -> TripProgress:
        progress = self._repository.get_progress(trip_id)
        if progress is None:
            raise TripNotFoundError(f"Trip not found: {trip_id}")
        return progress


trip_service = TripService(trip_repository)
