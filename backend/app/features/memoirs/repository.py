"""PostgreSQL persistence for memoirs and their shareable assets."""

from datetime import datetime, timezone
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import MemoirPhoto, MemoirShare, TravelMemoir, Trip
from app.db.session import SessionLocal


class MemoirRepository:
    @staticmethod
    def _query():
        return select(TravelMemoir).options(
            selectinload(TravelMemoir.photos), selectinload(TravelMemoir.shares)
        )

    def get_by_trip(self, trip_id: str) -> TravelMemoir | None:
        with SessionLocal() as session:
            return session.scalar(self._query().where(TravelMemoir.trip_id == trip_id))

    def get(self, memoir_id: str) -> TravelMemoir | None:
        with SessionLocal() as session:
            return session.scalar(self._query().where(TravelMemoir.id == memoir_id))

    def create(self, record: TravelMemoir) -> TravelMemoir:
        with SessionLocal() as session:
            session.add(record)
            session.commit()
            return session.scalar(self._query().where(TravelMemoir.id == record.id))

    def update(self, memoir_id: str, values: dict) -> TravelMemoir | None:
        with SessionLocal() as session:
            record = session.get(TravelMemoir, memoir_id)
            if record is None:
                return None
            for key, value in values.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            session.commit()
            return session.scalar(self._query().where(TravelMemoir.id == memoir_id))

    def add_photo(self, photo: MemoirPhoto) -> MemoirPhoto:
        with SessionLocal() as session:
            session.add(photo)
            session.commit()
            session.refresh(photo)
            return photo

    def get_photo(self, photo_id: str) -> MemoirPhoto | None:
        with SessionLocal() as session:
            return session.get(MemoirPhoto, photo_id)

    def delete_photo(self, photo_id: str) -> bool:
        with SessionLocal() as session:
            photo = session.get(MemoirPhoto, photo_id)
            if photo is None:
                return False
            session.delete(photo)
            session.commit()
            return True

    def create_share(self, memoir_id: str, privacy: dict) -> MemoirShare:
        with SessionLocal() as session:
            active = session.scalars(
                select(MemoirShare).where(
                    MemoirShare.memoir_id == memoir_id, MemoirShare.revoked_at.is_(None)
                )
            ).all()
            now = datetime.now(timezone.utc)
            for share in active:
                share.revoked_at = now
            share = MemoirShare(
                memoir_id=memoir_id, token=token_urlsafe(32), privacy=privacy
            )
            session.add(share)
            session.commit()
            session.refresh(share)
            return share

    def revoke_shares(self, memoir_id: str) -> bool:
        with SessionLocal() as session:
            records = session.scalars(
                select(MemoirShare).where(
                    MemoirShare.memoir_id == memoir_id, MemoirShare.revoked_at.is_(None)
                )
            ).all()
            if not records:
                return False
            now = datetime.now(timezone.utc)
            for record in records:
                record.revoked_at = now
            session.commit()
            return True

    def get_by_share(self, token: str) -> tuple[TravelMemoir, MemoirShare] | None:
        with SessionLocal() as session:
            share = session.scalar(
                select(MemoirShare).where(
                    MemoirShare.token == token, MemoirShare.revoked_at.is_(None)
                )
            )
            if share is None:
                return None
            memoir = session.scalar(self._query().where(TravelMemoir.id == share.memoir_id))
            return (memoir, share) if memoir is not None else None

    def trip(self, trip_id: str) -> Trip | None:
        with SessionLocal() as session:
            return session.get(Trip, trip_id)


memoir_repository = MemoirRepository()
