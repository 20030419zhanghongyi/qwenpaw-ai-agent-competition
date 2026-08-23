"""Add privacy-minimised long-term preference memory to users.

Revision: 20260822_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260822_01"
down_revision: Union[str, Sequence[str], None] = "20260725_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preference_memory", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preference_memory")
