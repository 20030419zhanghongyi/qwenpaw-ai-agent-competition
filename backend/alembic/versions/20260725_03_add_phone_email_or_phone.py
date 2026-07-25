"""Make email nullable; add phone; enforce email-or-phone constraint.

Revision: 20260725_03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_03"
down_revision: Union[str, Sequence[str], None] = "20260725_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make email nullable (was NOT NULL)
    op.alter_column("users", "email", existing_type=sa.String(256), nullable=True)
    # Drop existing unique constraint (auto-named) and re-create as partial
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # 2. Add phone column (nullable, unique — NULLs are distinct in PG)
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])

    # 3. CHECK: at least one of email or phone must be non-null
    op.create_check_constraint(
        "ck_users_email_or_phone",
        "users",
        "email IS NOT NULL OR phone IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_email_or_phone", "users", type_="check")
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_column("users", "phone")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.alter_column("users", "email", existing_type=sa.String(256), nullable=False)
