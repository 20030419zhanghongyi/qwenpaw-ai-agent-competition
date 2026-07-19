"""add persisted privacy-scrubbed postcards

Revision ID: 20260718_01
Revises: 20260716_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260718_01"
down_revision: str | Sequence[str] | None = "20260716_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "postcards",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("poi_id", sa.String(length=128), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("caption_source", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("review_decision", sa.String(length=16), nullable=False),
        sa.Column("image_svg", sa.LargeBinary(), nullable=False),
        sa.Column("photo_scrubbed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.UniqueConstraint("trip_id", "poi_id", name="uq_postcards_trip_poi"),
    )
    op.create_index("ix_postcards_trip_id", "postcards", ["trip_id"])
    op.create_index("ix_postcards_poi_id", "postcards", ["poi_id"])


def downgrade() -> None:
    op.drop_index("ix_postcards_poi_id", table_name="postcards")
    op.drop_index("ix_postcards_trip_id", table_name="postcards")
    op.drop_table("postcards")
