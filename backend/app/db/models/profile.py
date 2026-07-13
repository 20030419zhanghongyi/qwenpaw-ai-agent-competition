"""Favorite and trip feedback ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from .trip import Trip
    from .user import User


def uuid_string() -> str:
    return str(uuid4())


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "poi_id", name="uq_favorites_user_poi"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    poi_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="favorites")


class TripFeedback(Base):
    __tablename__ = "trip_feedback"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uq_trip_feedback_trip"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_reasonable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    walking_comfortable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
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

    trip: Mapped[Trip] = relationship(back_populates="feedback")
    user: Mapped[User] = relationship(back_populates="feedback")
