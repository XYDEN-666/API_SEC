"""create credentials table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("identity_name", sa.String(length=255), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="fk_credentials_target_id_targets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "target_id",
            "identity_name",
            name="uq_credentials_target_identity",
        ),
    )
    op.create_index(
        op.f("ix_credentials_target_id"),
        "credentials",
        ["target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_credentials_target_id"), table_name="credentials")
    op.drop_table("credentials")
