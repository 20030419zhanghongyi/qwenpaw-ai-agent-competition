"""add private travel memoirs, original photos, and revocable shares

Revision ID: 20260823_01
Revises: 20260822_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260823_01"
down_revision: str | Sequence[str] | None = "20260822_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "travel_memoirs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("style", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("introduction", sa.Text(), nullable=False, server_default=""),
        sa.Column("closing", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("chapters", sa.JSON(), nullable=False),
        sa.Column("cover_photo_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("trip_id", name="uq_travel_memoirs_trip_id"),
    )
    op.create_index("ix_travel_memoirs_trip_id", "travel_memoirs", ["trip_id"], unique=True)
    op.create_index("ix_travel_memoirs_user_id", "travel_memoirs", ["user_id"])
    op.create_table(
        "memoir_photos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("memoir_id", sa.String(length=36), nullable=False),
        sa.Column("poi_id", sa.String(length=128), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("has_people", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["memoir_id"], ["travel_memoirs.id"]),
    )
    op.create_index("ix_memoir_photos_memoir_id", "memoir_photos", ["memoir_id"])
    op.create_index("ix_memoir_photos_poi_id", "memoir_photos", ["poi_id"])
    op.create_table(
        "memoir_shares",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("memoir_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("privacy", sa.JSON(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["memoir_id"], ["travel_memoirs.id"]),
        sa.UniqueConstraint("token", name="uq_memoir_shares_token"),
    )
    op.create_index("ix_memoir_shares_memoir_id", "memoir_shares", ["memoir_id"])
    op.create_index("ix_memoir_shares_token", "memoir_shares", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("memoir_shares")
    op.drop_table("memoir_photos")
    op.drop_table("travel_memoirs")
