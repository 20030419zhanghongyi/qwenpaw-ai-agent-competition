"""create PostGIS POI table

Revision ID: 20260713_02
Revises: 20260713_01
"""

from collections.abc import Sequence

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa

revision: str = "20260713_02"
down_revision: str | Sequence[str] | None = "20260713_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "pois",
        sa.Column("poi_id", sa.String(length=64), nullable=False),
        sa.Column("poi_name", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("poi_id", name="pk_pois"),
    )
    op.create_index("ix_pois_poi_name", "pois", ["poi_name"])
    op.create_index("ix_pois_category", "pois", ["category"])
    op.create_index("ix_pois_location", "pois", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_pois_location", table_name="pois", postgresql_using="gist")
    op.drop_index("ix_pois_category", table_name="pois")
    op.drop_index("ix_pois_poi_name", table_name="pois")
    op.drop_table("pois")
