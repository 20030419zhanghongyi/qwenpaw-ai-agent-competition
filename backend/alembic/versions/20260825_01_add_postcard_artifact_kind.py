"""allow story artifacts to coexist with ordinary postcards

Revision ID: 20260825_01
Revises: 20260823_01
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_01"
down_revision: str | None = "20260823_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "postcards",
        sa.Column(
            "artifact_kind",
            sa.String(length=32),
            server_default="postcard",
            nullable=False,
        ),
    )
    op.drop_constraint("uq_postcards_trip_poi", "postcards", type_="unique")
    op.create_unique_constraint(
        "uq_postcards_trip_poi_kind",
        "postcards",
        ["trip_id", "poi_id", "artifact_kind"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_postcards_trip_poi_kind", "postcards", type_="unique")
    op.create_unique_constraint(
        "uq_postcards_trip_poi", "postcards", ["trip_id", "poi_id"]
    )
    op.drop_column("postcards", "artifact_kind")
