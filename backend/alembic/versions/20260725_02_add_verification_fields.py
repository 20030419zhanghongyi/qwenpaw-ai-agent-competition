"""Add verification_status, verification_code, verification_expires_at to users.

Revision: 20260725_02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_02"
down_revision: Union[str, Sequence[str], None] = "20260725_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "verification_status",
            sa.String(16),
            nullable=False,
            server_default="unverified",
        ),
    )
    op.add_column(
        "users",
        sa.Column("verification_code", sa.String(128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "verification_expires_at")
    op.drop_column("users", "verification_code")
    op.drop_column("users", "verification_status")
