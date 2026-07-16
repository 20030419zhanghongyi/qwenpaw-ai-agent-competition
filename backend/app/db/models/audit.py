"""De-identified audit records for model-backed requests."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(48), nullable=False)
    subject_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(128), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(48), nullable=True)
    input_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
