"""add user profile fields (name + preference JSON)

Revision ID: 20260714_01
Revises: 20260713_03

为「用户落库 + 极简登录」补两个字段：
- name：登录标识/昵称（最小必要，见 AI 伦理「注册只采集登录标识 + 语言」）
- preference：完整偏好 JSON（Preference 模型整体持久化，避免逐字段映射 ORM）
原有 travel_type/duration_minutes/interests 列保留不动（向后兼容）。
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260714_01"
down_revision: str | Sequence[str] | None = "20260713_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("preference", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preference")
    op.drop_column("users", "name")
