"""Persist direct account ownership on postcards.

Revision ID: 20260827_01
Revises: 20260826_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260827_01"
down_revision: str | Sequence[str] | None = "20260826_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("postcards", sa.Column("user_id", sa.String(length=64), nullable=True))
    op.execute(
        """
        UPDATE postcards
        SET user_id = trips.user_id
        FROM trips
        WHERE postcards.trip_id = trips.id
        """
    )
    op.alter_column("postcards", "user_id", existing_type=sa.String(length=64), nullable=False)
    op.create_foreign_key(
        "fk_postcards_user_id_users",
        "postcards",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index("ix_postcards_user_id", "postcards", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_postcards_user_id", table_name="postcards")
    op.drop_constraint("fk_postcards_user_id_users", "postcards", type_="foreignkey")
    op.drop_column("postcards", "user_id")
