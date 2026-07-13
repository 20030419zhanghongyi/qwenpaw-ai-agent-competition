"""PostgreSQL persistence for profile favorites and trip feedback."""

from collections.abc import Callable
from threading import RLock

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Favorite as FavoriteRecord
from app.db.models import TripFeedback as FeedbackRecord
from app.db.models import User as UserRecord
from app.db.session import SessionLocal

from .models import FavoritePoi, TripFeedback


class SqlAlchemyProfileRepository:
    """Persist profile state while exposing the existing domain models."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory
        self._created_favorite_ids: set[str] = set()
        self._created_feedback_ids: set[str] = set()
        self._created_ids_lock = RLock()

    @staticmethod
    def _favorite_to_domain(record: FavoriteRecord) -> FavoritePoi:
        return FavoritePoi(
            user_id=record.user_id,
            poi_id=record.poi_id,
            created_at=record.created_at,
        )

    @staticmethod
    def _feedback_to_domain(record: FeedbackRecord) -> TripFeedback:
        return TripFeedback(
            feedback_id=record.id,
            trip_id=record.trip_id,
            user_id=record.user_id,
            rating=record.rating,
            comment=record.comment,
            route_reasonable=record.route_reasonable,
            walking_comfortable=record.walking_comfortable,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _ensure_user(session: Session, user_id: str) -> None:
        if session.get(UserRecord, user_id) is None:
            session.add(UserRecord(id=user_id, interests=[]))

    def add_favorite(self, favorite: FavoritePoi) -> tuple[FavoritePoi, bool]:
        with self._session_factory() as session:
            existing = session.scalar(
                select(FavoriteRecord).where(
                    FavoriteRecord.user_id == favorite.user_id,
                    FavoriteRecord.poi_id == favorite.poi_id,
                )
            )
            if existing is not None:
                return self._favorite_to_domain(existing), False

            self._ensure_user(session, favorite.user_id)
            record = FavoriteRecord(
                user_id=favorite.user_id,
                poi_id=favorite.poi_id,
                created_at=favorite.created_at,
            )
            session.add(record)
            session.commit()
            result = self._favorite_to_domain(record)
            record_id = record.id

        with self._created_ids_lock:
            self._created_favorite_ids.add(record_id)
        return result, True

    def remove_favorite(self, user_id: str, poi_id: str) -> bool:
        with self._session_factory() as session:
            record = session.scalar(
                select(FavoriteRecord).where(
                    FavoriteRecord.user_id == user_id,
                    FavoriteRecord.poi_id == poi_id,
                )
            )
            if record is None:
                return False
            record_id = record.id
            session.delete(record)
            session.commit()
        with self._created_ids_lock:
            self._created_favorite_ids.discard(record_id)
        return True

    def list_favorites(self, user_id: str) -> list[FavoritePoi]:
        with self._session_factory() as session:
            records = session.scalars(
                select(FavoriteRecord)
                .where(FavoriteRecord.user_id == user_id)
                .order_by(FavoriteRecord.created_at.desc())
            ).all()
            return [self._favorite_to_domain(record) for record in records]

    def upsert_feedback(self, feedback: TripFeedback) -> tuple[TripFeedback, bool]:
        with self._session_factory() as session:
            record = session.scalar(
                select(FeedbackRecord).where(FeedbackRecord.trip_id == feedback.trip_id)
            )
            created = record is None
            if record is None:
                record = FeedbackRecord(
                    id=feedback.feedback_id,
                    trip_id=feedback.trip_id,
                    user_id=feedback.user_id,
                    rating=feedback.rating,
                    comment=feedback.comment,
                    route_reasonable=feedback.route_reasonable,
                    walking_comfortable=feedback.walking_comfortable,
                    created_at=feedback.created_at,
                    updated_at=feedback.updated_at,
                )
                session.add(record)
            else:
                record.rating = feedback.rating
                record.comment = feedback.comment
                record.route_reasonable = feedback.route_reasonable
                record.walking_comfortable = feedback.walking_comfortable
                record.updated_at = feedback.updated_at

            session.commit()
            result = self._feedback_to_domain(record)
            record_id = record.id

        if created:
            with self._created_ids_lock:
                self._created_feedback_ids.add(record_id)
        return result, created

    def get_feedback(self, trip_id: str) -> TripFeedback | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(FeedbackRecord).where(FeedbackRecord.trip_id == trip_id)
            )
            return self._feedback_to_domain(record) if record is not None else None

    def clear(self) -> None:
        """Remove only profile records created through this repository process."""
        with self._created_ids_lock:
            favorite_ids = set(self._created_favorite_ids)
            feedback_ids = set(self._created_feedback_ids)
            self._created_favorite_ids.clear()
            self._created_feedback_ids.clear()
        if not favorite_ids and not feedback_ids:
            return
        with self._session_factory() as session:
            if feedback_ids:
                session.execute(
                    delete(FeedbackRecord).where(FeedbackRecord.id.in_(feedback_ids))
                )
            if favorite_ids:
                session.execute(
                    delete(FavoriteRecord).where(FavoriteRecord.id.in_(favorite_ids))
                )
            session.commit()


profile_repository = SqlAlchemyProfileRepository()
