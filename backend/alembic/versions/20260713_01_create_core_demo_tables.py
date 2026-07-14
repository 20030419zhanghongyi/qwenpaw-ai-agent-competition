"""create core demo tables

Revision ID: 20260713_01
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260713_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("travel_type", sa.String(length=64), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_table(
        "trips",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("route_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_trips_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_trips"),
    )
    op.create_index("ix_trips_route_id", "trips", ["route_id"])
    op.create_index("ix_trips_status", "trips", ["status"])
    op.create_index("ix_trips_user_id", "trips", ["user_id"])
    op.create_table(
        "trip_stops",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("poi_id", sa.String(length=128), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="fk_trip_stops_trip_id_trips"),
        sa.PrimaryKeyConstraint("id", name="pk_trip_stops"),
        sa.UniqueConstraint("trip_id", "stop_order", name="uq_trip_stops_trip_order"),
    )
    op.create_index("ix_trip_stops_poi_id", "trip_stops", ["poi_id"])
    op.create_index("ix_trip_stops_trip_id", "trip_stops", ["trip_id"])
    op.create_table(
        "checkins",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("poi_id", sa.String(length=128), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="fk_checkins_trip_id_trips"),
        sa.PrimaryKeyConstraint("id", name="pk_checkins"),
        sa.UniqueConstraint("trip_id", "poi_id", name="uq_checkins_trip_poi"),
    )
    op.create_index("ix_checkins_poi_id", "checkins", ["poi_id"])
    op.create_index("ix_checkins_trip_id", "checkins", ["trip_id"])
    op.create_table(
        "favorites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("poi_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_favorites_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_favorites"),
        sa.UniqueConstraint("user_id", "poi_id", name="uq_favorites_user_poi"),
    )
    op.create_index("ix_favorites_poi_id", "favorites", ["poi_id"])
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    op.create_table(
        "trip_feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("route_reasonable", sa.Boolean(), nullable=True),
        sa.Column("walking_comfortable", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name=op.f("ck_trip_feedback_rating_range"),
        ),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="fk_trip_feedback_trip_id_trips"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_trip_feedback_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_trip_feedback"),
        sa.UniqueConstraint("trip_id", name="uq_trip_feedback_trip"),
    )
    op.create_index("ix_trip_feedback_user_id", "trip_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_trip_feedback_user_id", table_name="trip_feedback")
    op.drop_table("trip_feedback")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_index("ix_favorites_poi_id", table_name="favorites")
    op.drop_table("favorites")
    op.drop_index("ix_checkins_trip_id", table_name="checkins")
    op.drop_index("ix_checkins_poi_id", table_name="checkins")
    op.drop_table("checkins")
    op.drop_index("ix_trip_stops_trip_id", table_name="trip_stops")
    op.drop_index("ix_trip_stops_poi_id", table_name="trip_stops")
    op.drop_table("trip_stops")
    op.drop_index("ix_trips_user_id", table_name="trips")
    op.drop_index("ix_trips_status", table_name="trips")
    op.drop_index("ix_trips_route_id", table_name="trips")
    op.drop_table("trips")
    op.drop_table("users")
