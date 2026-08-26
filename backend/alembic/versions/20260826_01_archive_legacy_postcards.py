"""Archive postcards created by the retired rendering pipeline.

Revision ID: 20260826_01
Revises: 20260823_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_01"
down_revision: str | Sequence[str] | None = "20260823_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "postcards",
        sa.Column("render_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.drop_constraint("uq_postcards_trip_poi", "postcards", type_="unique")
    op.create_unique_constraint(
        "uq_postcards_trip_poi_version",
        "postcards",
        ["trip_id", "poi_id", "render_version"],
    )
    op.create_index("ix_postcards_render_version", "postcards", ["render_version"])


def downgrade() -> None:
    op.drop_index("ix_postcards_render_version", table_name="postcards")
    op.drop_constraint("uq_postcards_trip_poi_version", "postcards", type_="unique")
    # Keep the newest rendering for each trip and POI before restoring the old schema.
    op.execute(
        """
        DELETE FROM postcards AS older
        USING postcards AS newer
        WHERE older.trip_id = newer.trip_id
          AND older.poi_id = newer.poi_id
          AND older.render_version < newer.render_version
        """
    )
    op.drop_column("postcards", "render_version")
    op.create_unique_constraint(
        "uq_postcards_trip_poi",
        "postcards",
        ["trip_id", "poi_id"],
    )
