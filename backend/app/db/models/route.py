"""Database-backed route templates and ordered POI stops."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


def uuid_string() -> str:
    return str(uuid4())


class RouteTemplate(Base):
    __tablename__ = "route_templates"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    walk_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    physical_level: Mapped[str] = mapped_column(String(32), nullable=False)
    suitable_for: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
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

    stops: Mapped[list[RouteTemplateStop]] = relationship(
        back_populates="route_template",
        cascade="all, delete-orphan",
        order_by="RouteTemplateStop.stop_order",
    )


class RouteTemplateStop(Base):
    __tablename__ = "route_template_stops"
    __table_args__ = (
        UniqueConstraint(
            "route_template_id",
            "order",
            name="uq_route_template_stops_template_order",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    route_template_id: Mapped[str] = mapped_column(
        ForeignKey("route_templates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    poi_id: Mapped[str] = mapped_column(
        ForeignKey("pois.poi_id"), index=True, nullable=False
    )
    stop_order: Mapped[int] = mapped_column("order", Integer, nullable=False)
    stay_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    replaceable_with: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    route_template: Mapped[RouteTemplate] = relationship(back_populates="stops")
