"""Business rules for profile history, favorites, and feedback."""

from datetime import datetime, timezone
from uuid import uuid4

from app.db.session import SessionLocal
from app.features.pois.models import PoiResponse
from app.features.pois.repository import PoiRepository
from app.features.trips.models import TripStatus
from app.features.trips.repository import SqlAlchemyTripRepository
from app.features.trips.service import TripService
from app.features.trips.store import trip_store

from .models import (
    FavoritePoi,
    FavoritePoiResponse,
    HistoryTripResponse,
    TripFeedback,
    TripFeedbackRequest,
)
from .repository import SqlAlchemyProfileRepository, profile_repository


class PoiNotFoundError(LookupError):
    pass


class TripNotFoundError(LookupError):
    pass


class FeedbackNotFoundError(LookupError):
    pass


class TripUserMismatchError(PermissionError):
    pass


class TripNotCompletedError(RuntimeError):
    pass


class ProfileService:
    def __init__(
        self,
        repository: SqlAlchemyProfileRepository,
        trips: SqlAlchemyTripRepository,
    ) -> None:
        self._repository = repository
        self._trips = trips

    def list_trip_history(
        self,
        user_id: str,
        status: TripStatus | None,
        limit: int,
    ) -> list[HistoryTripResponse]:
        trips = self._trips.list_by_user(user_id)
        if status is not None:
            trips = [trip for trip in trips if trip.status == status]
        trips.sort(key=lambda trip: trip.created_at, reverse=True)

        history: list[HistoryTripResponse] = []
        for trip in trips[:limit]:
            progress = TripService.calculate_progress(trip)
            history.append(
                HistoryTripResponse(
                    trip_id=trip.trip_id,
                    route_id=trip.route_id,
                    status=trip.status,
                    created_at=trip.created_at,
                    updated_at=trip.updated_at,
                    total_stops=progress.total_stops,
                    completed_stops=progress.completed_stops,
                    completion_ratio=progress.completion_ratio,
                )
            )
        return history

    @staticmethod
    def _favorite_response(favorite: FavoritePoi, poi: PoiResponse) -> FavoritePoiResponse:
        return FavoritePoiResponse(
            user_id=favorite.user_id,
            poi_id=favorite.poi_id,
            poi_name=poi.poi_name,
            longitude=poi.longitude,
            latitude=poi.latitude,
            created_at=favorite.created_at,
        )

    def add_favorite(self, user_id: str, poi_id: str) -> tuple[FavoritePoiResponse, bool]:
        with SessionLocal() as session:
            poi = PoiRepository(session).get_by_id(poi_id)
        if poi is None:
            raise PoiNotFoundError(f"POI not found: {poi_id}")
        favorite, created = self._repository.add_favorite(
            FavoritePoi(
                user_id=user_id,
                poi_id=poi_id,
                created_at=datetime.now(timezone.utc),
            )
        )
        return self._favorite_response(favorite, poi), created

    def remove_favorite(self, user_id: str, poi_id: str) -> None:
        self._repository.remove_favorite(user_id, poi_id)

    def list_favorites(self, user_id: str) -> list[FavoritePoiResponse]:
        favorites = self._repository.list_favorites(user_id)
        with SessionLocal() as session:
            pois = PoiRepository(session).get_by_ids(
                [favorite.poi_id for favorite in favorites]
            )
        return [
            self._favorite_response(favorite, pois[favorite.poi_id])
            for favorite in favorites
            if favorite.poi_id in pois
        ]

    def upsert_feedback(
        self,
        trip_id: str,
        request: TripFeedbackRequest,
    ) -> tuple[TripFeedback, bool]:
        trip = self._trips.get(trip_id)
        if trip is None:
            raise TripNotFoundError(f"Trip not found: {trip_id}")
        if request.user_id != trip.user_id:
            raise TripUserMismatchError(f"Trip {trip_id} does not belong to user")
        if trip.status != TripStatus.COMPLETED:
            raise TripNotCompletedError(f"Trip is not completed: {trip_id}")

        now = datetime.now(timezone.utc)
        feedback = TripFeedback(
            feedback_id=str(uuid4()),
            trip_id=trip_id,
            user_id=request.user_id,
            rating=request.rating,
            comment=request.comment,
            route_reasonable=request.route_reasonable,
            walking_comfortable=request.walking_comfortable,
            created_at=now,
            updated_at=now,
        )
        return self._repository.upsert_feedback(feedback)

    def get_feedback(self, trip_id: str) -> TripFeedback:
        if self._trips.get(trip_id) is None:
            raise TripNotFoundError(f"Trip not found: {trip_id}")
        feedback = self._repository.get_feedback(trip_id)
        if feedback is None:
            raise FeedbackNotFoundError(f"Feedback not found for trip: {trip_id}")
        return feedback


profile_service = ProfileService(profile_repository, trip_store)
