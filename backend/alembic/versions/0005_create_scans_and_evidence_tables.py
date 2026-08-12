"""create scans and evidence tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="fk_scans_target_id_targets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scans_target_id"), "scans", ["target_id"], unique=False
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("scanner_name", sa.String(length=100), nullable=False),
        sa.Column("request_data", sa.Text(), nullable=True),
        sa.Column("response_data", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="fk_evidence_scan_id_scans",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_scan_id"), "evidence", ["scan_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_scan_id"), table_name="evidence")
    op.drop_table("evidence")
    op.drop_index(op.f("ix_scans_target_id"), table_name="scans")
    op.drop_table("scans")
