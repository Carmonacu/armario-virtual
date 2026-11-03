"""default new users to Spanish

This fork's UI default is es (see app/data/locales.json). Existing rows keep the
locale they already stored. Only the column default for future inserts changes.

Revision ID: b8e1c4a92f10
Revises: a7d3c9e1f5b2
Create Date: 2026-11-03 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b8e1c4a92f10"
down_revision: str | None = "a7d3c9e1f5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "locale", server_default="es")


def downgrade() -> None:
    op.alter_column("users", "locale", server_default="en")
