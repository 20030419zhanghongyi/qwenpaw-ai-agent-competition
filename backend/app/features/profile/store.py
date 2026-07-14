"""Process-local storage for favorites and trip feedback."""

from threading import RLock

from .models import FavoritePoi, TripFeedback


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._favorites: dict[tuple[str, str], FavoritePoi] = {}
        self._feedback_by_trip: dict[str, TripFeedback] = {}
        self._lock = RLock()

    def add_favorite(self, favorite: FavoritePoi) -> tuple[FavoritePoi, bool]:
        key = (favorite.user_id, favorite.poi_id)
        with self._lock:
            existing = self._favorites.get(key)
            if existing is not None:
                return existing.model_copy(deep=True), False
            self._favorites[key] = favorite.model_copy(deep=True)
            return favorite.model_copy(deep=True), True

    def remove_favorite(self, user_id: str, poi_id: str) -> bool:
        with self._lock:
            return self._favorites.pop((user_id, poi_id), None) is not None

    def is_favorite(self, user_id: str, poi_id: str) -> bool:
        with self._lock:
            return (user_id, poi_id) in self._favorites

    def list_favorites(self, user_id: str) -> list[FavoritePoi]:
        with self._lock:
            favorites = [
                favorite.model_copy(deep=True)
                for favorite in self._favorites.values()
                if favorite.user_id == user_id
            ]
        return sorted(favorites, key=lambda favorite: favorite.created_at, reverse=True)

    def upsert_feedback(self, feedback: TripFeedback) -> tuple[TripFeedback, bool]:
        with self._lock:
            existing = self._feedback_by_trip.get(feedback.trip_id)
            if existing is not None:
                feedback.feedback_id = existing.feedback_id
                feedback.created_at = existing.created_at
                created = False
            else:
                created = True
            self._feedback_by_trip[feedback.trip_id] = feedback.model_copy(deep=True)
            return feedback.model_copy(deep=True), created

    def get_feedback(self, trip_id: str) -> TripFeedback | None:
        with self._lock:
            feedback = self._feedback_by_trip.get(trip_id)
            return feedback.model_copy(deep=True) if feedback else None

    def clear(self) -> None:
        with self._lock:
            self._favorites.clear()
            self._feedback_by_trip.clear()


# Preserve the existing import path for test cleanup while active profile state
# moves to PostgreSQL.
from .repository import profile_repository  # noqa: E402

profile_store = profile_repository
