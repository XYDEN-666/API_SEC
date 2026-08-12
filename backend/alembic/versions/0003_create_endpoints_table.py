"""create endpoints table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "endpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="fk_endpoints_target_id_targets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "target_id",
            "path",
            "method",
            name="uq_endpoints_target_path_method",
        ),
    )
    op.create_index(
        op.f("ix_endpoints_target_id"), "endpoints", ["target_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_endpoints_target_id"), table_name="endpoints")
    op.drop_table("endpoints")
