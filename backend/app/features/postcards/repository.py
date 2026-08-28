"""PostgreSQL persistence for rendered postcard assets."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Postcard
from app.db.session import SessionLocal

CURRENT_POSTCARD_RENDER_VERSION = 2


class PostcardRepository:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def get(self, postcard_id: str) -> Postcard | None:
        with self._session_factory() as session:
            return session.scalar(
                select(Postcard).where(
                    Postcard.id == postcard_id,
                    Postcard.render_version == CURRENT_POSTCARD_RENDER_VERSION,
                )
            )

    def get_any_version(self, postcard_id: str) -> Postcard | None:
        with self._session_factory() as session:
            return session.get(Postcard, postcard_id)

    def get_for_trip_poi(self, trip_id: str, poi_id: str) -> Postcard | None:
        with self._session_factory() as session:
            return session.scalar(
                select(Postcard).where(
                    Postcard.trip_id == trip_id,
                    Postcard.poi_id == poi_id,
                    Postcard.render_version == CURRENT_POSTCARD_RENDER_VERSION,
                )
            )

    def list_by_trip(self, trip_id: str) -> list[Postcard]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Postcard)
                    .where(
                        Postcard.trip_id == trip_id,
                        Postcard.render_version == CURRENT_POSTCARD_RENDER_VERSION,
                    )
                    .order_by(Postcard.stop_order, Postcard.created_at, Postcard.id)
                )
            )

    def list_by_user(self, user_id: str) -> list[Postcard]:
        """Return every persisted postcard belonging to the account, newest first."""
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Postcard)
                    .where(Postcard.user_id == user_id)
                    .order_by(Postcard.created_at.desc(), Postcard.id.desc())
                )
            )

    def list_reusable_scene_candidates(self, poi_id: str, limit: int = 10) -> list[Postcard]:
        """Return recent no-upload cards that may contain a reusable AI scene."""
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Postcard)
                    .where(
                        Postcard.poi_id == poi_id,
                        Postcard.photo_scrubbed.is_(False),
                        Postcard.render_version == CURRENT_POSTCARD_RENDER_VERSION,
                    )
                    .order_by(Postcard.created_at.desc(), Postcard.id.desc())
                    .limit(limit)
                )
            )

    def create(self, postcard: Postcard) -> Postcard:
        with self._session_factory() as session:
            session.add(postcard)
            session.commit()
            session.refresh(postcard)
            return postcard

    def delete(self, postcard_id: str) -> bool:
        with self._session_factory() as session:
            record = session.get(Postcard, postcard_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    def delete_for_trip_poi(self, trip_id: str, poi_id: str) -> bool:
        with self._session_factory() as session:
            record = session.scalar(
                select(Postcard).where(
                    Postcard.trip_id == trip_id,
                    Postcard.poi_id == poi_id,
                    Postcard.render_version == CURRENT_POSTCARD_RENDER_VERSION,
                )
            )
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True


postcard_repository = PostcardRepository()
