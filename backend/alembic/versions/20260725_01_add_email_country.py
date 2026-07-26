"""Add email, country to users; make name NOT NULL.

Revision: 20260725_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_01"
down_revision: Union[str, Sequence[str], None] = "20260722_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add email column (nullable first, fill, then NOT NULL + UNIQUE)
    op.add_column("users", sa.Column("email", sa.String(256), nullable=True))
    # Fill existing rows with placeholder emails based on user_id
    op.execute(
        "UPDATE users SET email = 'user_' || id || '@placeholder.local' WHERE email IS NULL"
    )
    op.alter_column("users", "email", nullable=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # 2. Add country column (nullable, no existing data to backfill)
    op.add_column("users", sa.Column("country", sa.String(8), nullable=True))

    # 3. Make name NOT NULL — backfill existing NULLs with default
    op.execute("UPDATE users SET name = '未命名用户' WHERE name IS NULL")
    op.alter_column("users", "name", existing_type=sa.String(128), nullable=False)


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "email")
    op.drop_column("users", "country")
    op.alter_column("users", "name", existing_type=sa.String(128), nullable=True)
