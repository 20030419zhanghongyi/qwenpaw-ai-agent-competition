"""Trip, ordered stop, and check-in ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func
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
    postcards: Mapped[list[Postcard]] = relationship(back_populates="trip")
    memoir: Mapped[TravelMemoir | None] = relationship(back_populates="trip", uselist=False)
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


class Postcard(Base):
    """A privacy-scrubbed, shareable postcard generated from a completed trip stop."""

    __tablename__ = "postcards"
    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "poi_id",
            "render_version",
            name="uq_postcards_trip_poi_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True, nullable=False)
    poi_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    caption_source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    review_decision: Mapped[str] = mapped_column(String(16), nullable=False)
    image_svg: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    photo_scrubbed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    render_version: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    trip: Mapped[Trip] = relationship(back_populates="postcards")
    user: Mapped[User] = relationship(back_populates="postcards")


class TravelMemoir(Base):
    """Editable, private-by-default memoir for one Macau trip."""

    __tablename__ = "travel_memoirs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    trip_id: Mapped[str] = mapped_column(
        ForeignKey("trips.id"), unique=True, index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    style: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    introduction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    closing: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    chapters: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    cover_photo_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
        server_default=func.now(), nullable=False
    )

    trip: Mapped[Trip] = relationship(back_populates="memoir")
    photos: Mapped[list[MemoirPhoto]] = relationship(
        back_populates="memoir", cascade="all, delete-orphan"
    )
    shares: Mapped[list[MemoirShare]] = relationship(
        back_populates="memoir", cascade="all, delete-orphan"
    )


class MemoirPhoto(Base):
    __tablename__ = "memoir_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    memoir_id: Mapped[str] = mapped_column(
        ForeignKey("travel_memoirs.id"), index=True, nullable=False
    )
    poi_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    has_people: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    memoir: Mapped[TravelMemoir] = relationship(back_populates="photos")


class MemoirShare(Base):
    __tablename__ = "memoir_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    memoir_id: Mapped[str] = mapped_column(
        ForeignKey("travel_memoirs.id"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    privacy: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    memoir: Mapped[TravelMemoir] = relationship(back_populates="shares")
