"""add persisted story-route sessions

Revision ID: 20260722_01
Revises: 20260718_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260722_01"
down_revision: str | Sequence[str] | None = "20260718_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "story_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("story_id", sa.String(length=128), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("current_chapter_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.UniqueConstraint("trip_id", name="uq_story_sessions_trip_id"),
    )
    op.create_index("ix_story_sessions_user_id", "story_sessions", ["user_id"])
    op.create_index("ix_story_sessions_story_id", "story_sessions", ["story_id"])
    op.create_index("ix_story_sessions_status", "story_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_story_sessions_status", table_name="story_sessions")
    op.drop_index("ix_story_sessions_story_id", table_name="story_sessions")
    op.drop_index("ix_story_sessions_user_id", table_name="story_sessions")
    op.drop_table("story_sessions")
