"""PostgreSQL persistence for Demo trips and check-ins."""

from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Checkin as CheckinRecord
from app.db.models import Postcard as PostcardRecord
from app.db.models import Trip as TripRecord
from app.db.models import TripStop as TripStopRecord
from app.db.models import User as UserRecord
from app.db.session import SessionLocal

from .models import Trip, TripProgress, TripStatus


class SqlAlchemyTripRepository:
    """Store trip state in PostgreSQL while exposing domain models to services."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory
        self._created_trip_ids: set[str] = set()
        self._created_ids_lock = RLock()

    @staticmethod
    def _trip_query():
        return select(TripRecord).options(
            selectinload(TripRecord.stops),
            selectinload(TripRecord.checkins),
        )

    @staticmethod
    def _to_domain(record: TripRecord) -> Trip:
        stops = sorted(record.stops, key=lambda stop: stop.stop_order)
        checkins = sorted(
            record.checkins,
            key=lambda checkin: (checkin.checked_in_at, checkin.id),
        )
        return Trip(
            trip_id=record.id,
            user_id=record.user_id,
            route_id=record.route_id,
            status=TripStatus(record.status),
            stop_poi_ids=[stop.poi_id for stop in stops],
            checked_in_poi_ids=[checkin.poi_id for checkin in checkins],
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _calculate_progress(trip: Trip) -> TripProgress:
        checked = set(trip.checked_in_poi_ids)
        completed = sum(poi_id in checked for poi_id in trip.stop_poi_ids)
        total = len(trip.stop_poi_ids)
        return TripProgress(
            total_stops=total,
            completed_stops=completed,
            completion_ratio=completed / total if total else 0.0,
            next_poi_id=next(
                (poi_id for poi_id in trip.stop_poi_ids if poi_id not in checked),
                None,
            ),
        )

    def create_trip(self, trip: Trip) -> Trip:
        with self._session_factory() as session:
            if session.get(UserRecord, trip.user_id) is None:
                session.add(UserRecord(id=trip.user_id, interests=[]))

            record = TripRecord(
                id=trip.trip_id,
                user_id=trip.user_id,
                route_id=trip.route_id,
                status=trip.status.value,
                created_at=trip.created_at,
                updated_at=trip.updated_at,
            )
            record.stops = [
                TripStopRecord(poi_id=poi_id, stop_order=stop_order)
                for stop_order, poi_id in enumerate(trip.stop_poi_ids)
            ]
            session.add(record)
            session.commit()
            result = self._to_domain(record)

        with self._created_ids_lock:
            self._created_trip_ids.add(trip.trip_id)
        return result

    def get_trip(self, trip_id: str) -> Trip | None:
        with self._session_factory() as session:
            record = session.scalar(
                self._trip_query().where(TripRecord.id == trip_id)
            )
            return self._to_domain(record) if record is not None else None

    def get_user_current_trip(self, user_id: str) -> Trip | None:
        with self._session_factory() as session:
            record = session.scalar(
                self._trip_query()
                .where(
                    TripRecord.user_id == user_id,
                    TripRecord.status == TripStatus.ACTIVE.value,
                )
                .order_by(TripRecord.created_at.desc())
                .limit(1)
            )
            return self._to_domain(record) if record is not None else None

    def add_checkin(self, trip_id: str, poi_id: str) -> Trip | None:
        with self._session_factory() as session:
            record = session.scalar(
                self._trip_query().where(TripRecord.id == trip_id)
            )
            if record is None:
                return None

            if all(checkin.poi_id != poi_id for checkin in record.checkins):
                record.checkins.append(CheckinRecord(poi_id=poi_id))
                record.updated_at = datetime.now(timezone.utc)
                if len(record.checkins) == len(record.stops):
                    record.status = TripStatus.COMPLETED.value
                session.commit()
            return self._to_domain(record)

    def get_progress(self, trip_id: str) -> TripProgress | None:
        trip = self.get_trip(trip_id)
        return self._calculate_progress(trip) if trip is not None else None

    # Compatibility methods for the existing profile service and test fixtures.
    def get(self, trip_id: str) -> Trip | None:
        return self.get_trip(trip_id)

    def list_by_user(self, user_id: str) -> list[Trip]:
        with self._session_factory() as session:
            records = session.scalars(
                self._trip_query().where(TripRecord.user_id == user_id)
            ).all()
            return [self._to_domain(record) for record in records]

    def clear(self) -> None:
        """Remove only trips created through this repository process."""
        with self._created_ids_lock:
            trip_ids = set(self._created_trip_ids)
            self._created_trip_ids.clear()
        if not trip_ids:
            return
        with self._session_factory() as session:
            session.execute(delete(PostcardRecord).where(PostcardRecord.trip_id.in_(trip_ids)))
            session.execute(delete(CheckinRecord).where(CheckinRecord.trip_id.in_(trip_ids)))
            session.execute(delete(TripStopRecord).where(TripStopRecord.trip_id.in_(trip_ids)))
            session.execute(delete(TripRecord).where(TripRecord.id.in_(trip_ids)))
            session.commit()


trip_repository = SqlAlchemyTripRepository()
