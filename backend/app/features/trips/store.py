"""Process-local storage for Demo trips."""

from threading import RLock

from .models import Trip, TripStatus


class InMemoryTripStore:
    """Keep trip state behind a small replaceable storage interface."""

    def __init__(self) -> None:
        self._trips: dict[str, Trip] = {}
        self._lock = RLock()

    def create(self, trip: Trip) -> Trip:
        with self._lock:
            if trip.trip_id in self._trips:
                raise ValueError(f"Trip already exists: {trip.trip_id}")
            self._trips[trip.trip_id] = trip.model_copy(deep=True)
            return trip.model_copy(deep=True)

    def get(self, trip_id: str) -> Trip | None:
        with self._lock:
            trip = self._trips.get(trip_id)
            return trip.model_copy(deep=True) if trip else None

    def get_active_by_user(self, user_id: str) -> Trip | None:
        with self._lock:
            active = [
                trip
                for trip in self._trips.values()
                if trip.user_id == user_id and trip.status == TripStatus.ACTIVE
            ]
            if not active:
                return None
            latest = max(active, key=lambda trip: trip.created_at)
            return latest.model_copy(deep=True)

    def list_by_user(self, user_id: str) -> list[Trip]:
        with self._lock:
            return [
                trip.model_copy(deep=True)
                for trip in self._trips.values()
                if trip.user_id == user_id
            ]

    def update(self, trip: Trip) -> Trip:
        with self._lock:
            if trip.trip_id not in self._trips:
                raise KeyError(f"Trip not found: {trip.trip_id}")
            self._trips[trip.trip_id] = trip.model_copy(deep=True)
            return trip.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._trips.clear()


trip_store = InMemoryTripStore()
