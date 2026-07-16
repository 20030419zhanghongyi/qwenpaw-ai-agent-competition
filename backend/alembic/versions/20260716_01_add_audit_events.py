"""add de-identified audit events

Revision ID: 20260716_01
Revises: 20260714_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260716_01"
down_revision: str | Sequence[str] | None = "20260714_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("kind", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("subject_hash", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("decision", sa.String(length=48), nullable=True),
        sa.Column("input_chars", sa.Integer(), nullable=True),
        sa.Column("output_chars", sa.Integer(), nullable=True),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_kind", "audit_events", ["kind"])
    op.create_index("ix_audit_events_subject_hash", "audit_events", ["subject_hash"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_subject_hash", table_name="audit_events")
    op.drop_index("ix_audit_events_kind", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_table("audit_events")
