"""Reconcile postcard artifact columns after the merged migration histories.

Revision ID: 20260828_01
Revises: 20260827_01
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260828_01"
down_revision: str | Sequence[str] | None = "20260827_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("postcards")}
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("postcards")
    }

    if "artifact_kind" not in columns:
        op.add_column(
            "postcards",
            sa.Column(
                "artifact_kind",
                sa.String(length=32),
                server_default="postcard",
                nullable=False,
            ),
        )

    for legacy_name in ("uq_postcards_trip_poi", "uq_postcards_trip_poi_version"):
        if legacy_name in constraints:
            op.drop_constraint(legacy_name, "postcards", type_="unique")

    if "uq_postcards_trip_poi_kind_version" not in constraints:
        op.create_unique_constraint(
            "uq_postcards_trip_poi_kind_version",
            "postcards",
            ["trip_id", "poi_id", "artifact_kind", "render_version"],
        )


def downgrade() -> None:
    # This revision reconciles two previously released migration histories.
    # Earlier revisions own the columns and constraints, so downgrade is a no-op.
    pass
