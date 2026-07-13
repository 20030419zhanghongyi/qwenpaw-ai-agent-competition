"""Trip, ordered stop, and check-in ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from .profile import TripFeedback
    from .user import User


def uuid_string() -> str:
    return str(uuid4())


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    route_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="trips")
    stops: Mapped[list[TripStop]] = relationship(back_populates="trip")
    checkins: Mapped[list[Checkin]] = relationship(back_populates="trip")
    feedback: Mapped[TripFeedback | None] = relationship(back_populates="trip", uselist=False)


class TripStop(Base):
    __tablename__ = "trip_stops"
    __table_args__ = (
        UniqueConstraint("trip_id", "stop_order", name="uq_trip_stops_trip_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    poi_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    trip: Mapped[Trip] = relationship(back_populates="stops")


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("trip_id", "poi_id", name="uq_checkins_trip_poi"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    poi_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    trip: Mapped[Trip] = relationship(back_populates="checkins")
