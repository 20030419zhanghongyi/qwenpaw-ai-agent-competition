"""PostgreSQL persistence for rendered postcard assets."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Postcard
from app.db.session import SessionLocal


class PostcardRepository:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def get(self, postcard_id: str) -> Postcard | None:
        with self._session_factory() as session:
            return session.get(Postcard, postcard_id)

    def get_for_trip_poi(
        self,
        trip_id: str,
        poi_id: str,
        *,
        artifact_kind: str = "postcard",
    ) -> Postcard | None:
        with self._session_factory() as session:
            return session.scalar(
                select(Postcard).where(
                    Postcard.trip_id == trip_id,
                    Postcard.poi_id == poi_id,
                    Postcard.artifact_kind == artifact_kind,
                )
            )

    def list_by_trip(
        self, trip_id: str, *, artifact_kind: str = "postcard"
    ) -> list[Postcard]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Postcard)
                    .where(
                        Postcard.trip_id == trip_id,
                        Postcard.artifact_kind == artifact_kind,
                    )
                    .order_by(Postcard.stop_order, Postcard.created_at, Postcard.id)
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

    def delete_for_trip_poi(
        self,
        trip_id: str,
        poi_id: str,
        *,
        artifact_kind: str = "postcard",
    ) -> bool:
        with self._session_factory() as session:
            record = session.scalar(
                select(Postcard).where(
                    Postcard.trip_id == trip_id,
                    Postcard.poi_id == poi_id,
                    Postcard.artifact_kind == artifact_kind,
                )
            )
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True


postcard_repository = PostcardRepository()
