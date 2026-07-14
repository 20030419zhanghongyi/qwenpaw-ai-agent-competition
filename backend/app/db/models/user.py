"""User ORM model for the database foundation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from .profile import Favorite, TripFeedback
    from .trip import Trip


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # name + preference：用户落库 + 极简登录新增（迁移 20260714_01）。
    # preference 存完整 Preference（JSON），避免逐字段映射；旧列保留向后兼容。
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preference: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    travel_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
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

    trips: Mapped[list[Trip]] = relationship(back_populates="user")
    favorites: Mapped[list[Favorite]] = relationship(back_populates="user")
    feedback: Mapped[list[TripFeedback]] = relationship(back_populates="user")
