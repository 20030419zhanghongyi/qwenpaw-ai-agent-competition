"""Add password recovery question fields to users.

Revision ID: 20260831_01
Revises: 20260828_01
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_01"
down_revision: str | Sequence[str] | None = "20260828_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("security_question_id", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("security_answer_hash", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "security_answer_hash")
    op.drop_column("users", "security_question_id")
