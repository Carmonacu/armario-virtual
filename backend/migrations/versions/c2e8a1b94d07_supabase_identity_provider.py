"""allow supabase as a sign-in identity provider

Revision ID: c2e8a1b94d07
Revises: b8e1c4a92f10
Create Date: 2026-11-03 13:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c2e8a1b94d07"
down_revision: str | None = "b8e1c4a92f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_user_identities_provider", "user_identities", type_="check")
    op.create_check_constraint(
        "ck_user_identities_provider",
        "user_identities",
        "provider IN ('legacy', 'dev', 'oidc', 'forward_auth', 'supabase')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM user_identities WHERE provider = 'supabase'")
    op.drop_constraint("ck_user_identities_provider", "user_identities", type_="check")
    op.create_check_constraint(
        "ck_user_identities_provider",
        "user_identities",
        "provider IN ('legacy', 'dev', 'oidc', 'forward_auth')",
    )
