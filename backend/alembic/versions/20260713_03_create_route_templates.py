"""create database-backed route templates

Revision ID: 20260713_03
Revises: 20260713_02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260713_03"
down_revision: str | Sequence[str] | None = "20260713_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "route_templates",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("duration_hours", sa.Float(), nullable=False),
        sa.Column("walk_distance_km", sa.Float(), nullable=False),
        sa.Column("physical_level", sa.String(length=32), nullable=False),
        sa.Column("suitable_for", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_route_templates"),
    )
    op.create_index("ix_route_templates_duration", "route_templates", ["duration"])
    op.create_index("ix_route_templates_category", "route_templates", ["category"])
    op.create_table(
        "route_template_stops",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("route_template_id", sa.String(length=128), nullable=False),
        sa.Column("poi_id", sa.String(length=64), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("stay_minutes", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("replaceable_with", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["poi_id"], ["pois.poi_id"], name="fk_route_template_stops_poi_id_pois"
        ),
        sa.ForeignKeyConstraint(
            ["route_template_id"],
            ["route_templates.id"],
            name="fk_route_template_stops_route_template_id_route_templates",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_route_template_stops"),
        sa.UniqueConstraint(
            "route_template_id",
            "order",
            name="uq_route_template_stops_template_order",
        ),
    )
    op.create_index(
        "ix_route_template_stops_route_template_id",
        "route_template_stops",
        ["route_template_id"],
    )
    op.create_index(
        "ix_route_template_stops_poi_id", "route_template_stops", ["poi_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_route_template_stops_poi_id", table_name="route_template_stops")
    op.drop_index(
        "ix_route_template_stops_route_template_id", table_name="route_template_stops"
    )
    op.drop_table("route_template_stops")
    op.drop_index("ix_route_templates_category", table_name="route_templates")
    op.drop_index("ix_route_templates_duration", table_name="route_templates")
    op.drop_table("route_templates")
