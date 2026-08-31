"""User ORM model for the database foundation."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from .profile import Favorite, TripFeedback
    from .trip import Postcard, Trip


DEFAULT_GUEST_USER_NAME = "Guest traveler"


def guest_user_email(user_id: str) -> str:
    """Return a deterministic non-login email for an anonymous local user."""
    digest = sha256(user_id.encode("utf-8")).hexdigest()[:32]
    return f"guest-{digest}@local.invalid"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # email：登录凭据之一（与 phone 二选一，迁移 20260725_03）
    email: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    # phone：登录凭据之一（与 email 二选一，迁移 20260725_03）
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    # password_hash：bcrypt 哈希（迁移 20260725_04）
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    security_question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    security_answer_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # name + preference：用户落库 + 极简登录新增（迁移 20260714_01）。
    # preference 存完整 Preference（JSON），避免逐字段映射；旧列保留向后兼容。
    # name 改为必填（迁移 20260725_01）。
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    preference: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 仅保存从显式偏好、行程和反馈归纳出的结构化长期记忆；不保存原始对话。
    preference_memory: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # country：ISO 3166-1 alpha-2 国家码，用于个性化讲解（迁移 20260725_01）
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # verification：邮箱/手机验证状态（迁移 20260725_02）
    #   unverified / pending / verified — 默认 unverified
    verification_status: Mapped[str] = mapped_column(
        String(16), default="unverified", server_default="unverified", nullable=False
    )
    verification_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    postcards: Mapped[list[Postcard]] = relationship(back_populates="user")
    favorites: Mapped[list[Favorite]] = relationship(back_populates="user")
    feedback: Mapped[list[TripFeedback]] = relationship(back_populates="user")
