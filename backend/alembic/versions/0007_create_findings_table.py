"""create findings table

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=True),
        sa.Column("owasp_category", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name="fk_findings_evidence_id_evidence",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="fk_findings_scan_id_scans",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_findings_scan_id"), "findings", ["scan_id"], unique=False
    )
    op.create_index(
        op.f("ix_findings_evidence_id"),
        "findings",
        ["evidence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_evidence_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_scan_id"), table_name="findings")
    op.drop_table("findings")
